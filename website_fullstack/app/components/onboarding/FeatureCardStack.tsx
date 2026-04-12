'use client';

import { motion, Variants } from 'framer-motion';
import React from 'react';

interface Feature {
  icon: string;
  title: string;
  description: string;
}

interface FeatureCardStackProps {
  features: Feature[];
}

export default function FeatureCardStack({ features }: FeatureCardStackProps) {
  const containerVariants: Variants = {
    initial: {
      opacity: 0,
    },
    animate: {
      opacity: 1,
      transition: {
        delay: 0.2,
        staggerChildren: 0.15,
      },
    },
  };

  // Card positions for a 5-card fan layout
  const cardPositions = [
    { rotate: -14, x: -175, y: 20, zIndex: 10 },
    { rotate: -7, x: -85, y: 8, zIndex: 20 },
    { rotate: 0, x: 0, y: 0, zIndex: 30 },
    { rotate: 7, x: 85, y: 8, zIndex: 40 },
    { rotate: 14, x: 175, y: 20, zIndex: 50 },
  ];

  const createCardVariants = (position: typeof cardPositions[0]): Variants => ({
    initial: { rotate: 0, x: 0, y: 0, opacity: 0 },
    animate: {
      rotate: position.rotate,
      x: position.x,
      y: position.y,
      opacity: 1,
      transition: {
        type: 'spring',
        stiffness: 120,
        damping: 12,
      },
    },
    hover: {
      y: position.y - 8,
      transition: {
        type: 'spring',
        stiffness: 200,
        damping: 15,
      },
    },
  });

  return (
    <motion.div
      className="relative flex items-center justify-center w-80 h-72 my-12"
      variants={containerVariants}
      initial="initial"
      animate="animate"
    >
      {features.map((feature, index) => (
        <motion.div
          key={feature.title}
          className="absolute w-40 h-56 bg-white rounded-2xl shadow-xl overflow-hidden flex flex-col justify-between p-5 origin-bottom"
          variants={createCardVariants(cardPositions[index])}
          whileHover="hover"
          style={{ zIndex: cardPositions[index].zIndex }}
        >
          <span className="text-4xl">{feature.icon}</span>
          <div>
            <p className="text-sm font-semibold text-black leading-tight">
              {feature.title}
            </p>
            <p className="text-xs text-black/60 mt-2 leading-relaxed">
              {feature.description}
            </p>
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}
