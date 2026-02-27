import { HeroSection } from "@/components/marketing/hero-section";
import { ProblemSection } from "@/components/marketing/problem-section";
import { FeaturesSection } from "@/components/marketing/features-section";
import { TestimonialsSection } from "@/components/marketing/testimonials-section";
import { PricingPreviewSection } from "@/components/marketing/pricing-preview";
import { CtaSection } from "@/components/marketing/cta-section";

/**
 * Landing page — assembles all marketing sections in order.
 * Inherits metadata from the (marketing) layout.
 */
export default function HomePage() {
  return (
    <>
      <HeroSection />
      <ProblemSection />
      <FeaturesSection />
      <TestimonialsSection />
      <PricingPreviewSection />
      <CtaSection />
    </>
  );
}
