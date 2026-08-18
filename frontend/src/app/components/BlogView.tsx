"use client";

import React from "react";
import { motion } from "framer-motion";
import { BookOpen, Sparkles, ArrowRight, Clock, User, Tag, TrendingUp } from "lucide-react";

export default function BlogView() {
  const articles = [
    {
      id: 1,
      title: "The End of Spec Hallucinations: How Deterministic RAG is Changing Gadget Shopping",
      excerpt: "Why traditional search engines struggle with complex datasheet comparisons, and how vector retrieval guarantees 100% factual accuracy.",
      category: "AI Engineering",
      readTime: "4 min read",
      author: "Swathi",
      date: "August 14, 2026",
      image: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=80",
      featured: true,
    },
    {
      id: 2,
      title: "Intel Core i7 13th Gen vs AMD Ryzen 7: 2026 Laptop Buyer's Guide",
      excerpt: "We put top silicon chips head-to-head to measure thermal throttling, battery efficiency, and gaming frame rates.",
      category: "Hardware Review",
      readTime: "6 min read",
      author: "Tech Editorial",
      date: "August 10, 2026",
      image: "https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=600&auto=format&fit=crop&q=80",
    },
    {
      id: 3,
      title: "OLED vs IPS Displays: Is the Color Premium Worth It for Creators?",
      excerpt: "An objective breakdown of color gamuts, peak brightness, contrast ratios, and everyday burn-in risks.",
      category: "Display Tech",
      readTime: "5 min read",
      author: "Display Lab",
      date: "August 04, 2026",
      image: "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=600&auto=format&fit=crop&q=80",
    },
    {
      id: 4,
      title: "Building Zero-Hallucination Systems with Pinecone & LangChain",
      excerpt: "How we ingested thousands of verified brand datasheets into a multi-dimensional comparison graph.",
      category: "Engineering",
      readTime: "8 min read",
      author: "Dev Team",
      date: "July 28, 2026",
      image: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop&q=80",
    },
  ];

  const tags = ["AI", "Hardware", "Laptops", "Display Tech", "Engineering", "Reviews", "Trending"];

  return (
    <div className="py-8 space-y-10 pb-32">
      {/* Hero Header */}
      <div className="text-center max-w-2xl mx-auto space-y-4">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-50 border border-brand-200 text-brand-700 text-xs font-bold"
        >
          <BookOpen className="w-3.5 h-3.5 text-brand-600" />
          VersusAI Publications
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-4xl sm:text-5xl font-black tracking-tight text-slate-900"
        >
          Tech <span className="gradient-text">Magazine</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-slate-600 font-medium text-base"
        >
          Deep-dive analyses, hardware benchmarks, and engineering breakdowns behind our comparison engine.
        </motion.p>

        {/* Tags */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex flex-wrap items-center justify-center gap-2 pt-2"
        >
          {tags.map((tag) => (
            <button
              key={tag}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:text-brand-600 hover:bg-brand-50 transition-all shadow-2xs"
            >
              <Tag className="w-3 h-3 text-slate-400" />
              {tag}
            </button>
          ))}
        </motion.div>
      </div>

      {/* Featured Article */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="bg-white border border-slate-200/90 rounded-3xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 group cursor-pointer hover:shadow-xl transition-all"
      >
        <div className="lg:col-span-7 h-72 lg:h-auto overflow-hidden relative bg-slate-100">
          <img
            src={articles[0].image}
            alt={articles[0].title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
          />
          <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-md px-3 py-1.5 rounded-xl text-xs font-bold text-brand-600 flex items-center gap-1.5 shadow-md">
            <Sparkles className="w-3.5 h-3.5" /> Featured Story
          </div>
        </div>

        <div className="lg:col-span-5 p-8 flex flex-col justify-between space-y-6">
          <div className="space-y-3">
            <div className="flex items-center gap-4 text-xs font-bold text-slate-500">
              <span className="text-brand-600 uppercase tracking-wider">{articles[0].category}</span>
              <span>•</span>
              <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" /> {articles[0].readTime}</span>
            </div>
            <h2 className="text-2xl font-black text-slate-900 group-hover:text-brand-600 transition-colors leading-snug">
              {articles[0].title}
            </h2>
            <p className="text-slate-600 text-sm font-medium leading-relaxed">{articles[0].excerpt}</p>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-700">
              <User className="w-4 h-4 text-slate-400" /> {articles[0].author}
            </div>
            <span className="flex items-center gap-1.5 text-sm font-black text-brand-600 group-hover:translate-x-1 transition-transform">
              Read Article <ArrowRight className="w-4 h-4" />
            </span>
          </div>
        </div>
      </motion.div>

      {/* Grid of Articles */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {articles.slice(1).map((article, i) => (
          <motion.div
            key={article.id}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 + i * 0.1 }}
            className="bg-white border border-slate-200/90 rounded-3xl overflow-hidden flex flex-col justify-between group cursor-pointer hover:shadow-xl transition-all p-5"
          >
            <div>
              <div className="h-48 w-full rounded-2xl overflow-hidden mb-5 bg-slate-100 relative">
                <img
                  src={article.image}
                  alt={article.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
              </div>

              <div className="flex items-center gap-3 text-[11px] font-bold text-slate-500 mb-2">
                <span className="text-brand-600 uppercase tracking-wider">{article.category}</span>
                <span>•</span>
                <span>{article.readTime}</span>
              </div>

              <h3 className="text-lg font-black text-slate-900 group-hover:text-brand-600 transition-colors leading-snug mb-2">
                {article.title}
              </h3>

              <p className="text-slate-600 text-sm font-medium leading-relaxed">{article.excerpt}</p>
            </div>

            <div className="flex items-center justify-between pt-5 mt-5 border-t border-slate-100 text-xs font-bold text-slate-500">
              <div className="flex items-center gap-2">
                <User className="w-3.5 h-3.5 text-slate-400" /> {article.author}
              </div>
              <span className="text-brand-600 flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                Read More <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Newsletter Card */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="bg-gradient-to-br from-brand-600 via-indigo-600 to-cyan-600 rounded-3xl p-8 sm:p-12 text-center text-white space-y-4 shadow-xl shadow-brand-500/20"
      >
        <div className="w-12 h-12 rounded-2xl bg-white/10 backdrop-blur-md flex items-center justify-center mx-auto">
          <TrendingUp className="w-6 h-6 text-white" />
        </div>
        <h3 className="text-2xl sm:text-3xl font-black">Stay in the Loop</h3>
        <p className="text-white/80 font-medium text-sm max-w-md mx-auto">
          Get weekly hardware benchmarks, price alert highlights, and engineering deep-dives delivered to your inbox.
        </p>
        <div className="flex items-center gap-3 max-w-md mx-auto pt-2">
          <input
            type="email"
            placeholder="your@email.com"
            className="flex-1 px-4 py-3.5 bg-white/10 border border-white/20 rounded-xl text-white text-sm font-medium focus:outline-none focus:ring-2 focus:ring-white/40 placeholder:text-white/60"
          />
          <button className="px-6 py-3.5 bg-white text-brand-700 rounded-xl font-extrabold text-sm hover:bg-slate-100 transition-all shadow-md">
            Subscribe
          </button>
        </div>
      </motion.div>
    </div>
  );
}
