import factory
from faker import Faker

fake = Faker("es_CO")


class PlanFactory(factory.Factory):
    class Meta:
        model = dict

    name = factory.Sequence(lambda n: f"Plan {n}")
    slug = factory.Sequence(lambda n: f"plan-{n}")
    max_patients = 50
    max_doctors = 1
    max_users = 2
    max_storage_mb = 100
    features = factory.LazyFunction(lambda: {"odontogram_classic": True})
    price_cents = 0


class TenantFactory(factory.Factory):
    class Meta:
        model = dict

    name = factory.LazyFunction(lambda: f"Clinica {fake.company()}")
    slug = factory.Sequence(lambda n: f"clinic-{n}")
    country_code = "CO"
    owner_email = factory.LazyFunction(lambda: fake.email())
