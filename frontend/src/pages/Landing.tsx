import { Features } from "@/components/landing/Features";
import { Footer } from "@/components/landing/Footer";
import { Hero } from "@/components/landing/Hero";
import { Nav } from "@/components/landing/Nav";
import { Pipeline } from "@/components/landing/Pipeline";
import { StackStrip } from "@/components/landing/StackStrip";

export default function Landing() {
  return (
    <div className="min-h-dvh">
      <Nav />
      <main>
        <Hero />
        <Pipeline />
        <Features />
        <StackStrip />
      </main>
      <Footer />
    </div>
  );
}
