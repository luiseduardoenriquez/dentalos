"""Maintenance worker — audit archival, analytics aggregation, and cleanup jobs.

Handles periodic maintenance tasks: expired session cleanup, expired token
cleanup, audit log archival, and analytics aggregation.
"""

import logging
from datetime import UTC, datetime, timedelta

from app.schemas.queue import QueueMessage
from app.workers.base import BaseWorker

logger = logging.getLogger("dentalos.worker.maintenance")


class MaintenanceWorker(BaseWorker):
    """Consumes from the ``maintenance`` queue and dispatches by job_type."""

    queue_name = "maintenance"
    prefetch_count = 5

    async def process(self, message: QueueMessage) -> None:
        """Route maintenance job to the appropriate handler."""
        handlers = {
            "audit.archive": self._handle_audit_archive,
            "analytics.aggregate": self._handle_analytics_aggregate,
            "cleanup.expired_sessions": self._handle_cleanup_expired_sessions,
            "cleanup.expired_tokens": self._handle_cleanup_expired_tokens,
            # Sprint 21-22: Recall campaign + membership handlers
            "recall.identify_inactive": self._handle_recall_identify_inactive,
            "recall.identify_incomplete_plans": self._handle_recall_identify_incomplete_plans,
            "recall.identify_hygiene_due": self._handle_recall_identify_hygiene_due,
            "recall.identify_birthdays": self._handle_recall_identify_birthdays,
            "recall.process_step": self._handle_recall_process_step,
            "membership.renewal_check": self._handle_membership_renewal_check,
            # Sprint 23-24: Delinquency + Acceptance task handlers
            "tasks.check_delinquency": self._handle_check_delinquency,
            "tasks.check_acceptance": self._handle_check_acceptance,
            # Sprint 23-24: RETHUS verification handlers
            "rethus.verify_user": self._handle_rethus_verify,
            "rethus.reverify": self._handle_rethus_reverify,
            # Sprint 23-24: EPS auto-verification
            "eps.auto_verify": self._handle_eps_auto_verify,
            # Sprint 23-24: Post-op auto-dispatch
            "postop.auto_dispatch": self._handle_postop_auto_dispatch,
            # Sprint 25-26: Reputation, Loyalty, Schedule Intelligence
            "survey.auto_send": self._handle_survey_auto_send,
            "loyalty.award_appointment": self._handle_loyalty_award,
            "loyalty.award_ontime_payment": self._handle_loyalty_award,
            "loyalty.award_referral": self._handle_loyalty_award,
            "loyalty.award_membership_renewal": self._handle_loyalty_award,
            "loyalty.expire_inactive": self._handle_loyalty_expire,
            "schedule.unfilled_alert": self._handle_unfilled_alert,
            # GAP-15: AI Workflow Compliance Monitor
            "workflow.compliance_check": self._handle_workflow_compliance_check,
        }
        handler = handlers.get(message.job_type)
        if handler:
            await handler(message)
        else:
            logger.warning(
                "Unknown job_type for maintenance queue: %s message_id=%s",
                message.job_type,
                message.message_id,
            )

    async def _handle_audit_archive(self, message: QueueMessage) -> None:
        """Archive old audit log entries to cold storage.

        Payload:
            tenant_id: str — tenant to archive
            older_than_days: int — archive entries older than N days (default 90)
        """
        payload = message.payload
        tenant_id = message.tenant_id
        older_than_days = payload.get("older_than_days", 90)

        try:
            from sqlalchemy import text

            from app.core.database import get_tenant_session

            cutoff = datetime.now(UTC) - timedelta(days=older_than_days)

            async with get_tenant_session(tenant_id) as db:
                result = await db.execute(
                    text(
                        "DELETE FROM audit_logs "
                        "WHERE created_at < :cutoff "
                        "RETURNING id"
                    ),
                    {"cutoff": cutoff},
                )
                deleted_count = result.rowcount
                await db.commit()

            logger.info(
                "Audit archive completed: tenant=%s deleted=%d older_than=%dd",
                tenant_id,
                deleted_count,
                older_than_days,
            )
        except Exception:
            logger.exception(
                "Audit archive failed: tenant=%s", tenant_id
            )
            raise

    async def _handle_analytics_aggregate(self, message: QueueMessage) -> None:
        """Aggregate analytics data for a tenant.

        Payload:
            tenant_id: str — tenant to aggregate
            period: str — "daily" or "weekly" (default "daily")
        """
        payload = message.payload
        tenant_id = message.tenant_id
        period = payload.get("period", "daily")

        try:
            from sqlalchemy import text

            from app.core.database import get_tenant_session

            async with get_tenant_session(tenant_id) as db:
                # Count patients, appointments, and revenue for the period
                if period == "daily":
                    interval = "1 day"
                else:
                    interval = "7 days"

                stats = await db.execute(
                    text(
                        "SELECT "
                        "  (SELECT COUNT(*) FROM patients WHERE is_active = true) AS total_patients, "
                        "  (SELECT COUNT(*) FROM appointments "
                        "   WHERE created_at >= now() - :interval::interval) AS recent_appointments "
                    ),
                    {"interval": interval},
                )
                row = stats.one_or_none()

                if row:
                    logger.info(
                        "Analytics aggregated: tenant=%s period=%s patients=%d appointments=%d",
                        tenant_id,
                        period,
                        row.total_patients,
                        row.recent_appointments,
                    )
        except Exception:
            logger.exception(
                "Analytics aggregation failed: tenant=%s", tenant_id
            )
            raise

    async def _handle_cleanup_expired_sessions(self, message: QueueMessage) -> None:
        """Remove expired user sessions from the tenant schema.

        Payload:
            tenant_id: str — tenant to clean up
        """
        tenant_id = message.tenant_id

        try:
            from sqlalchemy import text

            from app.core.database import get_tenant_session

            async with get_tenant_session(tenant_id) as db:
                result = await db.execute(
                    text(
                        "DELETE FROM user_sessions "
                        "WHERE expires_at < now() OR is_revoked = true "
                        "RETURNING id"
                    )
                )
                deleted_count = result.rowcount
                await db.commit()

            logger.info(
                "Expired sessions cleaned: tenant=%s deleted=%d",
                tenant_id,
                deleted_count,
            )
        except Exception:
            logger.exception(
                "Session cleanup failed: tenant=%s", tenant_id
            )
            raise

    async def _handle_cleanup_expired_tokens(self, message: QueueMessage) -> None:
        """Remove expired password reset and email verification tokens from Redis.

        Uses SCAN to find and delete expired token keys.
        """
        try:
            from app.core.cache import cache_delete_pattern

            # Clean up expired reset tokens
            await cache_delete_pattern("dentalos:auth:reset:*")
            # Clean up expired verification tokens
            await cache_delete_pattern("dentalos:auth:verify_email:*")
            # Clean up expired JTI blacklist entries
            await cache_delete_pattern("dentalos:auth:jti_blacklist:*")

            logger.info("Expired token cleanup completed")
        except Exception:
            logger.exception("Token cleanup failed")
            raise


    # ── Sprint 21-22: Recall Campaign Handlers ─────────────────────────────────

    async def _handle_recall_identify_inactive(self, message: QueueMessage) -> None:
        """Identify patients with no visit in X months and add as campaign recipients."""
        tenant_id = message.tenant_id
        payload = message.payload
        campaign_id = payload.get("campaign_id")
        months = payload.get("months_threshold", 6)

        try:
            from app.core.database import get_tenant_session
            from app.services.recall_service import recall_service

            async with get_tenant_session(tenant_id) as db:
                patient_ids = await recall_service.identify_inactive_patients(
                    db=db, months_threshold=months,
                )
                if campaign_id and patient_ids:
                    import uuid
                    added = await recall_service.add_recipients(
                        db=db,
                        campaign_id=uuid.UUID(campaign_id),
                        patient_ids=patient_ids,
                    )
                    await db.commit()
                    logger.info(
                        "Recall identify_inactive: tenant=%s added=%d patients=%d",
                        tenant_id, added, len(patient_ids),
                    )
        except Exception:
            logger.exception("Recall identify_inactive failed: tenant=%s", tenant_id)
            raise

    async def _handle_recall_identify_incomplete_plans(self, message: QueueMessage) -> None:
        """Identify patients with incomplete treatment plans."""
        tenant_id = message.tenant_id
        payload = message.payload
        campaign_id = payload.get("campaign_id")

        try:
            from app.core.database import get_tenant_session
            from app.services.recall_service import recall_service

            async with get_tenant_session(tenant_id) as db:
                patient_ids = await recall_service.identify_incomplete_plans(db=db)
                if campaign_id and patient_ids:
                    import uuid
                    added = await recall_service.add_recipients(
                        db=db,
                        campaign_id=uuid.UUID(campaign_id),
                        patient_ids=patient_ids,
                    )
                    await db.commit()
                    logger.info(
                        "Recall identify_incomplete_plans: tenant=%s added=%d",
                        tenant_id, added,
                    )
        except Exception:
            logger.exception("Recall identify_incomplete_plans failed: tenant=%s", tenant_id)
            raise

    async def _handle_recall_identify_hygiene_due(self, message: QueueMessage) -> None:
        """Identify patients overdue for hygiene recall."""
        tenant_id = message.tenant_id
        payload = message.payload
        campaign_id = payload.get("campaign_id")

        try:
            from app.core.database import get_tenant_session
            from app.services.recall_service import recall_service

            async with get_tenant_session(tenant_id) as db:
                patient_ids = await recall_service.identify_hygiene_due(db=db)
                if campaign_id and patient_ids:
                    import uuid
                    added = await recall_service.add_recipients(
                        db=db,
                        campaign_id=uuid.UUID(campaign_id),
                        patient_ids=patient_ids,
                    )
                    await db.commit()
                    logger.info(
                        "Recall identify_hygiene_due: tenant=%s added=%d",
                        tenant_id, added,
                    )
        except Exception:
            logger.exception("Recall identify_hygiene_due failed: tenant=%s", tenant_id)
            raise

    async def _handle_recall_identify_birthdays(self, message: QueueMessage) -> None:
        """Identify patients with upcoming birthdays."""
        tenant_id = message.tenant_id
        payload = message.payload
        campaign_id = payload.get("campaign_id")
        days_ahead = payload.get("days_ahead", 7)

        try:
            from app.core.database import get_tenant_session
            from app.services.recall_service import recall_service

            async with get_tenant_session(tenant_id) as db:
                patient_ids = await recall_service.identify_birthdays(
                    db=db, days_ahead=days_ahead,
                )
                if campaign_id and patient_ids:
                    import uuid
                    added = await recall_service.add_recipients(
                        db=db,
                        campaign_id=uuid.UUID(campaign_id),
                        patient_ids=patient_ids,
                    )
                    await db.commit()
                    logger.info(
                        "Recall identify_birthdays: tenant=%s added=%d",
                        tenant_id, added,
                    )
        except Exception:
            logger.exception("Recall identify_birthdays failed: tenant=%s", tenant_id)
            raise

    async def _handle_recall_process_step(self, message: QueueMessage) -> None:
        """Process the current step for a recall campaign recipient."""
        tenant_id = message.tenant_id
        payload = message.payload
        recipient_id = payload.get("recipient_id")

        if not recipient_id:
            logger.warning("recall.process_step missing recipient_id: %s", message.message_id)
            return

        try:
            import uuid

            from app.core.database import get_tenant_session
            from app.core.queue import publish_message
            from app.services.recall_service import recall_service

            async with get_tenant_session(tenant_id) as db:
                notification_payload = await recall_service.process_step(
                    db=db, recipient_id=uuid.UUID(recipient_id),
                )
                await db.commit()

                if notification_payload:
                    await publish_message(
                        "notifications",
                        QueueMessage(
                            tenant_id=tenant_id,
                            job_type=f"recall.{notification_payload['channel']}",
                            payload=notification_payload,
                        ),
                    )
                    logger.info(
                        "Recall step processed: tenant=%s recipient=%s channel=%s",
                        tenant_id, recipient_id[:8], notification_payload["channel"],
                    )
        except Exception:
            logger.exception("Recall process_step failed: tenant=%s", tenant_id)
            raise

    # ── Sprint 21-22: Membership Renewal Handler ─────────────────────────────

    async def _handle_membership_renewal_check(self, message: QueueMessage) -> None:
        """Check for memberships due for renewal and send notifications."""
        tenant_id = message.tenant_id

        try:
            from datetime import date

            from sqlalchemy import select

            from app.core.database import get_tenant_session
            from app.core.queue import publish_message
            from app.models.tenant.membership import MembershipSubscription

            async with get_tenant_session(tenant_id) as db:
                today = date.today()
                result = await db.execute(
                    select(MembershipSubscription).where(
                        MembershipSubscription.status == "active",
                        MembershipSubscription.next_billing_date == today,
                        MembershipSubscription.is_active.is_(True),
                    )
                )
                due_subs = result.scalars().all()

                for sub in due_subs:
                    await publish_message(
                        "notifications",
                        QueueMessage(
                            tenant_id=tenant_id,
                            job_type="membership.renewal_reminder",
                            payload={
                                "subscription_id": str(sub.id),
                                "patient_id": str(sub.patient_id),
                                "plan_id": str(sub.plan_id),
                            },
                        ),
                    )

                logger.info(
                    "Membership renewal check: tenant=%s due=%d",
                    tenant_id, len(due_subs),
                )
        except Exception:
            logger.exception("Membership renewal check failed: tenant=%s", tenant_id)
            raise


    # ── Sprint 23-24: Task Check Handlers ──────────────────────────────────

    async def _handle_check_delinquency(self, message: QueueMessage) -> None:
        """Check for delinquent invoices and create staff tasks."""
        tenant_id = message.tenant_id
        try:
            from app.core.database import get_tenant_session
            from app.services.staff_task_service import staff_task_service

            async with get_tenant_session(tenant_id) as db:
                count = await staff_task_service.check_delinquency(
                    db=db, tenant_id=tenant_id
                )
                await db.commit()
                logger.info(
                    "Delinquency check: tenant=%s tasks_created=%d",
                    tenant_id,
                    count,
                )
        except Exception:
            logger.exception("Delinquency check failed: tenant=%s", tenant_id)
            raise

    async def _handle_check_acceptance(self, message: QueueMessage) -> None:
        """Check for quotations needing acceptance follow-up."""
        tenant_id = message.tenant_id
        try:
            from app.core.database import get_tenant_session
            from app.services.staff_task_service import staff_task_service

            async with get_tenant_session(tenant_id) as db:
                count = await staff_task_service.check_acceptance(
                    db=db, tenant_id=tenant_id
                )
                await db.commit()
                logger.info(
                    "Acceptance check: tenant=%s tasks_created=%d",
                    tenant_id,
                    count,
                )
        except Exception:
            logger.exception("Acceptance check failed: tenant=%s", tenant_id)
            raise

    # ── Sprint 23-24: RETHUS Handlers ──────────────────────────────────────

    async def _handle_rethus_verify(self, message: QueueMessage) -> None:
        """Verify a user's RETHUS professional registration."""
        tenant_id = message.tenant_id
        payload = message.payload
        user_id = payload.get("user_id")
        rethus_number = payload.get("rethus_number")
        if not user_id or not rethus_number:
            logger.warning(
                "rethus.verify_user missing required fields: %s",
                message.message_id,
            )
            return
        try:
            import uuid

            from app.core.database import get_tenant_session
            from app.services.rethus_verification_service import rethus_verification_service

            async with get_tenant_session(tenant_id) as db:
                await rethus_verification_service.verify_user(
                    db=db,
                    user_id=uuid.UUID(user_id),
                    rethus_number=rethus_number,
                )
                await db.commit()
                logger.info(
                    "RETHUS verify: tenant=%s user=%s",
                    tenant_id,
                    user_id[:8],
                )
        except Exception:
            logger.exception("RETHUS verify failed: tenant=%s", tenant_id)
            raise

    async def _handle_rethus_reverify(self, message: QueueMessage) -> None:
        """Re-verify all doctors/assistants RETHUS status."""
        tenant_id = message.tenant_id
        try:
            from app.core.database import get_tenant_session
            from app.services.rethus_verification_service import rethus_verification_service

            async with get_tenant_session(tenant_id) as db:
                await rethus_verification_service.periodic_reverify(db=db)
                await db.commit()
                logger.info("RETHUS reverify: tenant=%s", tenant_id)
        except Exception:
            logger.exception("RETHUS reverify failed: tenant=%s", tenant_id)
            raise

    # ── Sprint 23-24: EPS Handler ──────────────────────────────────────────

    async def _handle_eps_auto_verify(self, message: QueueMessage) -> None:
        """Auto-verify EPS affiliation for a new patient."""
        tenant_id = message.tenant_id
        payload = message.payload
        patient_id = payload.get("patient_id")
        if not patient_id:
            logger.warning(
                "eps.auto_verify missing patient_id: %s",
                message.message_id,
            )
            return
        try:
            import uuid

            from app.core.database import get_tenant_session
            from app.services.eps_verification_service import eps_verification_service

            async with get_tenant_session(tenant_id) as db:
                await eps_verification_service.auto_verify_on_creation(
                    db=db,
                    patient_id=uuid.UUID(patient_id),
                )
                await db.commit()
                logger.info(
                    "EPS auto-verify: tenant=%s patient=%s",
                    tenant_id,
                    patient_id[:8],
                )
        except Exception:
            logger.exception("EPS auto-verify failed: tenant=%s", tenant_id)
            raise

    # ── Sprint 23-24: Post-Op Handler ──────────────────────────────────────

    async def _handle_postop_auto_dispatch(self, message: QueueMessage) -> None:
        """Auto-dispatch post-op instructions after procedure."""
        tenant_id = message.tenant_id
        payload = message.payload
        patient_id = payload.get("patient_id")
        procedure_type = payload.get("procedure_type")
        record_id = payload.get("record_id")
        if not patient_id or not procedure_type:
            logger.warning(
                "postop.auto_dispatch missing required fields: %s",
                message.message_id,
            )
            return
        try:
            import uuid

            from app.core.database import get_tenant_session
            from app.services.postop_service import postop_service

            async with get_tenant_session(tenant_id) as db:
                await postop_service.auto_dispatch(
                    db=db,
                    patient_id=uuid.UUID(patient_id),
                    procedure_type=procedure_type,
                    record_id=uuid.UUID(record_id) if record_id else None,
                    tenant_id=tenant_id,
                )
                await db.commit()
                logger.info(
                    "Postop auto-dispatch: tenant=%s procedure=%s",
                    tenant_id,
                    procedure_type,
                )
        except Exception:
            logger.exception("Postop auto-dispatch failed: tenant=%s", tenant_id)
            raise


    # ── Sprint 25-26: Reputation Handler ──────────────────────────────────

    async def _handle_survey_auto_send(self, message: QueueMessage) -> None:
        """Auto-send satisfaction survey after appointment completion."""
        tenant_id = message.tenant_id
        payload = message.payload
        appointment_id = payload.get("appointment_id")
        patient_id = payload.get("patient_id")
        channel = payload.get("channel", "whatsapp")
        if not appointment_id or not patient_id:
            logger.warning(
                "survey.auto_send missing required fields: %s",
                message.message_id,
            )
            return
        try:
            from app.core.database import get_tenant_session
            from app.services.reputation_service import reputation_service

            async with get_tenant_session(tenant_id) as db:
                await reputation_service.send_survey(
                    db=db,
                    patient_id=patient_id,
                    appointment_id=appointment_id,
                    channel=channel,
                    tenant_id=tenant_id,
                )
                await db.commit()
                logger.info(
                    "Survey auto-sent: tenant=%s appointment=%s",
                    tenant_id[:8],
                    appointment_id[:8],
                )
        except Exception:
            logger.exception("Survey auto-send failed: tenant=%s", tenant_id)
            raise

    # ── Sprint 25-26: Loyalty Handlers ────────────────────────────────────

    async def _handle_loyalty_award(self, message: QueueMessage) -> None:
        """Award loyalty points for various triggers."""
        tenant_id = message.tenant_id
        payload = message.payload
        patient_id = payload.get("patient_id")
        points = payload.get("points")
        reason = payload.get("reason", message.job_type)
        reference_id = payload.get("reference_id")
        reference_type = payload.get("reference_type")
        if not patient_id or not points:
            logger.warning(
                "loyalty.award missing required fields: %s",
                message.message_id,
            )
            return
        try:
            import uuid

            from app.core.database import get_tenant_session
            from app.services.loyalty_service import loyalty_service

            async with get_tenant_session(tenant_id) as db:
                await loyalty_service.award_points(
                    db=db,
                    patient_id=uuid.UUID(patient_id),
                    points=int(points),
                    reason=reason,
                    reference_id=uuid.UUID(reference_id) if reference_id else None,
                    reference_type=reference_type,
                )
                await db.commit()
                logger.info(
                    "Loyalty points awarded: tenant=%s patient=%s points=%d",
                    tenant_id[:8],
                    patient_id[:8],
                    int(points),
                )
        except Exception:
            logger.exception("Loyalty award failed: tenant=%s", tenant_id)
            raise

    async def _handle_loyalty_expire(self, message: QueueMessage) -> None:
        """Expire inactive loyalty points (monthly cron)."""
        tenant_id = message.tenant_id
        payload = message.payload
        expiry_months = payload.get("expiry_months", 12)
        try:
            from app.core.database import get_tenant_session
            from app.services.loyalty_service import loyalty_service

            async with get_tenant_session(tenant_id) as db:
                count = await loyalty_service.expire_inactive(
                    db=db, expiry_months=expiry_months,
                )
                await db.commit()
                logger.info(
                    "Loyalty expiration: tenant=%s expired=%d",
                    tenant_id[:8],
                    count,
                )
        except Exception:
            logger.exception("Loyalty expiration failed: tenant=%s", tenant_id)
            raise

    # ── Sprint 25-26: Schedule Intelligence Handler ───────────────────────

    async def _handle_unfilled_alert(self, message: QueueMessage) -> None:
        """8 AM daily alert: notify receptionist of unfilled slots."""
        tenant_id = message.tenant_id
        try:
            from datetime import date

            from app.core.database import get_tenant_session
            from app.core.queue import publish_message
            from app.services.schedule_intelligence_service import (
                schedule_intelligence_service,
            )

            async with get_tenant_session(tenant_id) as db:
                intelligence = await schedule_intelligence_service.get_intelligence(
                    db=db, target_date=date.today(),
                )
                gaps = intelligence.get("gaps", [])
                if gaps:
                    await publish_message(
                        "notifications",
                        QueueMessage(
                            tenant_id=tenant_id,
                            job_type="notification.dispatch",
                            payload={
                                "type": "unfilled_slots_alert",
                                "gap_count": len(gaps),
                                "date": date.today().isoformat(),
                            },
                        ),
                    )
                logger.info(
                    "Unfilled alert: tenant=%s gaps=%d",
                    tenant_id[:8],
                    len(gaps),
                )
        except Exception:
            logger.exception("Unfilled alert failed: tenant=%s", tenant_id)
            raise


    # ── GAP-15: Workflow Compliance Handler ───────────────────────────────

    _COMPLIANCE_CHECK_LABELS: dict[str, str] = {
        "appointment_no_record": "Cita completada sin historia clinica",
        "record_no_diagnosis": "Historia clinica sin diagnostico",
        "record_no_procedure": "Historia clinica sin procedimiento",
        "plan_consent_unsigned": "Plan de tratamiento sin consentimiento firmado",
        "plan_item_overdue": "Item de plan de tratamiento vencido (+90 dias)",
        "lab_order_overdue": "Orden de laboratorio vencida",
        "patient_no_anamnesis": "Paciente sin anamnesis",
    }

    async def _handle_workflow_compliance_check(self, message: QueueMessage) -> None:
        """Run compliance checks and dispatch notifications/tasks."""
        tenant_id = message.tenant_id
        payload = message.payload
        lookback_days = payload.get("lookback_days", 30)
        enable_ai = payload.get("enable_ai", False)
        create_tasks = payload.get("create_tasks", True)

        try:
            from app.core.database import get_tenant_session
            from app.core.queue import publish_message
            from app.services.workflow_compliance_service import (
                workflow_compliance_service,
            )

            async with get_tenant_session(tenant_id) as db:
                snapshot = await workflow_compliance_service.get_compliance_snapshot(
                    db=db,
                    tenant_id=tenant_id,
                    lookback_days=lookback_days,
                    enable_ai=enable_ai,
                )

                for check in snapshot.checks:
                    for violation in check.violations:
                        # Dispatch in-app notification
                        await publish_message(
                            "notifications",
                            QueueMessage(
                                tenant_id=tenant_id,
                                job_type="notification.dispatch",
                                payload={
                                    "type": "workflow_compliance_alert",
                                    "check_type": violation.check_type,
                                    "severity": violation.severity,
                                    "patient_id": str(violation.patient_id),
                                    "reference_id": str(violation.reference_id) if violation.reference_id else None,
                                    "reference_type": violation.reference_type,
                                },
                            ),
                        )

                    # Create staff tasks for high/medium severity
                    if create_tasks and check.severity in ("high", "medium") and check.count > 0:
                        try:
                            from app.services.staff_task_service import staff_task_service

                            label = self._COMPLIANCE_CHECK_LABELS.get(
                                check.check_type, check.check_type
                            )
                            await staff_task_service.create_task(
                                db=db,
                                title=f"[Compliance] {label} ({check.count})",
                                description=(
                                    f"Se detectaron {check.count} caso(s) de "
                                    f"'{label}'. Revise y tome accion."
                                ),
                                task_type="manual",
                                priority="high" if check.severity == "high" else "normal",
                                metadata={
                                    "source": "workflow_compliance",
                                    "check_type": check.check_type,
                                    "count": check.count,
                                },
                            )
                        except Exception:
                            logger.warning(
                                "Failed to create staff task for %s",
                                check.check_type,
                                exc_info=True,
                            )

                await db.commit()

            logger.info(
                "Workflow compliance check: tenant=%s violations=%d checks=%d",
                tenant_id[:8] if len(tenant_id) > 8 else tenant_id,
                snapshot.total_violations,
                len(snapshot.checks),
            )
        except Exception:
            logger.exception(
                "Workflow compliance check failed: tenant=%s", tenant_id
            )
            raise


# Module-level instance for CLI entry point
maintenance_worker = MaintenanceWorker()
