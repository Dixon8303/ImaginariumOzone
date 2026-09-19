import Navbar from "@/components/site/Navbar";
import Footer from "@/components/site/Footer";
import Hero from "@/components/site/Hero";
import HowItWorks from "@/components/site/HowItWorks";
import Features from "@/components/site/Features";
import PricingSection from "@/components/site/PricingSection";
import FAQ from "@/components/site/FAQ";
import CTASection from "@/components/site/CTASection";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <Hero />
        <HowItWorks />
        <Features />
        <PricingSection />
        <FAQ />
        <CTASection />
      </main>
      <Footer />
    </div>
  );
}
