/**
 * Gauge Chart Component
 * =====================
 * Animated gauge visualization for health scores and metrics.
 * 
 * Features:
 * - Animated arc drawing
 * - Color-coded ranges (green/yellow/red)
 * - Customizable thresholds
 * - Responsive design
 */

import { useEffect, useState } from 'react';

interface GaugeChartProps {
  value: number; // 0-100
  label?: string;
  size?: number; // Diameter in pixels
  thickness?: number; // Arc thickness
  thresholds?: {
    green: number; // >= this value is green
    yellow: number; // >= this value is yellow, < green
    // < yellow is red
  };
}

export default function GaugeChart({
  value,
  label,
  size = 200,
  thickness = 20,
  thresholds = { green: 90, yellow: 70 },
}: GaugeChartProps) {
  const [animatedValue, setAnimatedValue] = useState(0);

  // Animate value on mount and change
  useEffect(() => {
    const duration = 1000; // 1 second
    const steps = 60;
    const stepDuration = duration / steps;
    const increment = value / steps;
    let currentStep = 0;

    const timer = setInterval(() => {
      currentStep++;
      setAnimatedValue(Math.min(value, increment * currentStep));
      
      if (currentStep >= steps) {
        clearInterval(timer);
      }
    }, stepDuration);

    return () => clearInterval(timer);
  }, [value]);

  // Calculate gauge properties
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  const arcLength = (animatedValue / 100) * circumference;
  const dashOffset = circumference - arcLength;

  // Determine color based on value
  const getColor = (val: number): string => {
    if (val >= thresholds.green) return '#10B981'; // green-500
    if (val >= thresholds.yellow) return '#F59E0B'; // yellow-500
    return '#EF4444'; // red-500
  };

  const color = getColor(value);

  // Label color
  const getLabelColor = (val: number): string => {
    if (val >= thresholds.green) return 'text-green-600';
    if (val >= thresholds.yellow) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        {/* Background circle */}
        <svg
          className="transform -rotate-90"
          width={size}
          height={size}
        >
          {/* Gray background arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#E5E7EB"
            strokeWidth={thickness}
          />
          
          {/* Colored value arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={thickness}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            className="transition-all duration-300"
          />
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-4xl font-bold ${getLabelColor(value)}`}>
            {animatedValue.toFixed(1)}
          </span>
          <span className="text-sm text-slate-500">از ۱۰۰</span>
        </div>
      </div>

      {/* Status label */}
      {label && (
        <div className="mt-4">
          <span className={`rounded-full px-3 py-1 text-sm font-medium ${
            value >= thresholds.green
              ? 'bg-green-100 text-green-700'
              : value >= thresholds.yellow
              ? 'bg-yellow-100 text-yellow-700'
              : 'bg-red-100 text-red-700'
          }`}>
            {label === 'healthy' ? 'سالم' : label === 'degraded' ? 'تنزل یافته' : 'بحرانی'}
          </span>
        </div>
      )}

      {/* Component scores breakdown */}
      <div className="mt-4 w-full space-y-1">
        <GaugeLabel color="#10B981" label="عالی (۹۰-۱۰۰)" />
        <GaugeLabel color="#F59E0B" label="متوسط (۷۰-۸۹)" />
        <GaugeLabel color="#EF4444" label="بحرانی (<۷۰)" />
      </div>
    </div>
  );
}

function GaugeLabel({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-600">
      <div
        className="h-3 w-3 rounded-full"
        style={{ backgroundColor: color }}
      />
      <span>{label}</span>
    </div>
  );
}