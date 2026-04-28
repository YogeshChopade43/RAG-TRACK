import { motion as Motion, AnimatePresence } from "framer-motion";
import "./HeroSection.css";

const HeroSection = ({ onUploadClick }) => {
  const handleLearnMore = () => {
    window.open("https://github.com/YogeshChopade43/RAG-TRACK#readme", "_blank", "noopener,noreferrer");
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.15,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 40 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.8,
        ease: [0.16, 1, 0.3, 1],
      },
    },
  };

  const titleVariants = {
    hidden: { opacity: 0, y: 60 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 1,
        ease: [0.16, 1, 0.3, 1],
      },
    },
  };

  const gradientTextVariants = {
    hidden: { opacity: 0, backgroundPosition: "0% 50%" },
    visible: {
      opacity: 1,
      backgroundPosition: "100% 50%",
      transition: {
        duration: 1.5,
        ease: "easeOut",
      },
    },
  };

  return (
    <section className="hero-section" aria-labelledby="hero-title">
      <div className="hero-content container">
        <Motion.div
          className="hero-badge"
          variants={itemVariants}
          initial="hidden"
          animate="visible"
        >
          <span className="badge-dot"></span>
          <span className="badge-text">AI-Powered Document Intelligence</span>
        </Motion.div>

        <Motion.h1
          id="hero-title"
          className="hero-title font-display"
          variants={titleVariants}
          initial="hidden"
          animate="visible"
        >
          <span className="title-line">
            <Motion.span
              className="text-gradient-gold"
              variants={gradientTextVariants}
              initial="hidden"
              animate="visible"
            >
              RAG-TRACK
            </Motion.span>
          </span>
          <span className="title-line" style={{ fontFamily: "var(--font-body)", fontWeight: "300", fontSize: "clamp(1.2rem, 3vw, 1.8rem)", letterSpacing: "0.2em", textTransform: "uppercase", marginTop: "var(--space-sm)" }}>
            Document Intelligence Platform
          </span>
        </Motion.h1>

        <Motion.p
          className="hero-description"
          variants={itemVariants}
          initial="hidden"
          animate="visible"
        >
          Upload any document and engage in intelligent conversations with its content.
          Experience the power of Retrieval-Augmented Generation for instant knowledge extraction.
        </Motion.p>

        <Motion.div
          className="hero-cta"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <Motion.button
            className="btn btn-primary"
            variants={itemVariants}
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={onUploadClick}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Upload Document
          </Motion.button>
          <Motion.a
            className="btn btn-secondary"
            variants={itemVariants}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.95 }}
            href="https://github.com/YogeshChopade43/RAG-TRACK#readme"
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleLearnMore}
          >
            Learn More
          </Motion.a>
        </Motion.div>

        <Motion.div
          className="hero-stats"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          <div className="stat-item">
            <span className="stat-number">99.7%</span>
            <span className="stat-label">Accuracy Rate</span>
          </div>
          <div className="stat-divider"></div>
          <div className="stat-item">
            <span className="stat-number">&lt;500ms</span>
            <span className="stat-label">Response Time</span>
          </div>
          <div className="stat-divider"></div>
          <div className="stat-item">
            <span className="stat-number">50+</span>
            <span className="stat-label">Formats Supported</span>
          </div>
        </Motion.div>
      </div>

      <div className="hero-visual">
        <div className="floating-card card-1">
          <div className="card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <div className="card-text">
            <span className="card-title">Query Decomposition</span>
            <span className="card-subtitle">Splits complex multi-part questions into focused sub-queries</span>
          </div>
        </div>

        <div className="floating-card card-2">
          <div className="card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5" />
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
              <path d="M16 21h5v-5" />
            </svg>
          </div>
          <div className="card-text">
            <span className="card-title">Query Rewriting</span>
            <span className="card-subtitle">Transforms conversational queries into optimized search terms</span>
          </div>
        </div>

        <div className="floating-card card-3">
          <div className="card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="16" />
              <line x1="8" y1="12" x2="16" y2="12" />
              <circle cx="12" cy="12" r="3" fill="currentColor" fill-opacity="0.3" />
            </svg>
          </div>
          <div className="card-text">
            <span className="card-title">Multi-Query Expansion</span>
            <span className="card-subtitle">Generates multiple query variations for comprehensive retrieval</span>
          </div>
        </div>

        <div className="floating-card card-4">
          <div className="card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="8" y1="13" x2="16" y2="13" />
              <line x1="8" y1="17" x2="16" y2="17" />
              <path d="M10 9h4" stroke="var(--color-gold-primary)" stroke-width="2" />
            </svg>
          </div>
          <div className="card-text">
            <span className="card-title">Page-Aware Chunking</span>
            <span className="card-subtitle">Smart splitting with accurate page number retention</span>
          </div>
        </div>

        <div className="floating-card card-5">
          <div className="card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </div>
          <div className="card-text">
            <span className="card-title">Observability Traces</span>
            <span className="card-subtitle">Full pipeline visibility with per-stage timing</span>
          </div>
        </div>

        <div className="floating-card card-6">
          <div className="card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
          </div>
          <div className="card-text">
            <span className="card-title">Citation Tracking</span>
            <span className="card-subtitle">Every answer includes source file and page references</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
