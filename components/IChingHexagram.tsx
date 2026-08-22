'use client';

import { motion } from 'framer-motion';

interface IChingHexagramProps {
  binaryString: string;
  wuxingPhase?: string;
}

const WUXING_GLOW_COLORS: Record<string, string> = {
  WATER: 'shadow-[0_0_10px_rgba(6,182,212,0.8)] bg-cyan-400',
  WOOD: 'shadow-[0_0_10px_rgba(74,222,128,0.8)] bg-green-400',
  FIRE: 'shadow-[0_0_10px_rgba(239,68,68,0.8)] bg-red-500',
  EARTH: 'shadow-[0_0_10px_rgba(202,138,4,0.8)] bg-yellow-500',
  METAL: 'shadow-[0_0_10px_rgba(229,231,235,0.8)] bg-gray-200',
};

export default function IChingHexagram({ binaryString, wuxingPhase = 'EARTH' }: IChingHexagramProps) {
  const safeBinary = /^[01]{6}$/.test(binaryString ?? '') ? binaryString : '000000';
  const yaoArray = safeBinary.split('').reverse();
  const glowClass = WUXING_GLOW_COLORS[wuxingPhase.toUpperCase()] ?? WUXING_GLOW_COLORS.EARTH;

  return (
    <div
      aria-label={`I Ching hexagram ${safeBinary}`}
      className="flex w-16 flex-col items-center justify-center space-y-1.5 rounded-md border border-white/10 bg-black/20 p-2 backdrop-blur-sm"
    >
      {yaoArray.map((yao, index) => {
        const isYang = yao === '1';
        const delay = (5 - index) * 0.1;

        return (
          <motion.div
            key={`${safeBinary}-${index}`}
            initial={{ opacity: 0, scaleX: 0, filter: 'blur(4px)' }}
            animate={{ opacity: 1, scaleX: 1, filter: 'blur(0px)' }}
            transition={{ duration: 0.4, delay, ease: 'easeOut' }}
            className="flex h-1.5 w-full items-center justify-between"
          >
            {isYang ? (
              <div className={`h-full w-full rounded-sm ${glowClass}`} />
            ) : (
              <>
                <div className={`h-full w-[45%] rounded-sm ${glowClass}`} />
                <div className={`h-full w-[45%] rounded-sm ${glowClass}`} />
              </>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}
