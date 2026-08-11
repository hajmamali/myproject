/**
 * MAHOUN Persian Language & RTL Utilities
 * 
 * Utilities for:
 * - Persian text processing
 * - RTL layout support
 * - Number formatting
 * - Date/time localization
 */

/**
 * Convert English numbers to Persian
 */
export function toPersianNumbers(input: string | number): string {
  const englishToPersian = {
    '0': '۰',
    '1': '۱',
    '2': '۲',
    '3': '۳',
    '4': '۴',
    '5': '۵',
    '6': '۶',
    '7': '۷',
    '8': '۸',
    '9': '۹',
  };

  return String(input).replace(/[0-9]/g, (match) => 
    englishToPersian[match as keyof typeof englishToPersian] || match
  );
}

/**
 * Convert Persian numbers to English
 */
export function toEnglishNumbers(input: string): string {
  const persianToEnglish = {
    '۰': '0',
    '۱': '1',
    '۲': '2',
    '۳': '3',
    '۴': '4',
    '۵': '5',
    '۶': '6',
    '۷': '7',
    '۸': '8',
    '۹': '9',
  };

  return input.replace(/[۰-۹]/g, (match) => 
    persianToEnglish[match as keyof typeof persianToEnglish] || match
  );
}

/**
 * Format Persian currency (Rial/Toman)
 */
export function formatPersianCurrency(
  amount: number,
  currency: 'rial' | 'toman' = 'toman',
  showSymbol: boolean = true
): string {
  const convertedAmount = currency === 'toman' ? amount / 10 : amount;
  const formatted = new Intl.NumberFormat('fa-IR').format(convertedAmount);
  const symbol = currency === 'toman' ? 'تومان' : 'ریال';
  
  return showSymbol ? `${formatted} ${symbol}` : formatted;
}

/**
 * Format Persian date
 */
export function formatPersianDate(
  date: Date | string,
  style: 'short' | 'medium' | 'long' = 'medium'
): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  try {
    const formatter = new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: style === 'short' ? 'numeric' : style === 'medium' ? 'short' : 'long',
      day: 'numeric',
      calendar: 'persian',
    });
    
    return formatter.format(dateObj);
  } catch {
    // Fallback to Georgian calendar if Persian calendar not supported
    const formatter = new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: style === 'short' ? 'numeric' : style === 'medium' ? 'short' : 'long',
      day: 'numeric',
    });
    
    return formatter.format(dateObj);
  }
}

/**
 * Format Persian time
 */
export function formatPersianTime(
  date: Date | string,
  includeSeconds: boolean = false
): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  const formatter = new Intl.DateTimeFormat('fa-IR', {
    hour: '2-digit',
    minute: '2-digit',
    ...(includeSeconds && { second: '2-digit' }),
    hour12: false,
  });
  
  return formatter.format(dateObj);
}

/**
 * Get text direction for a given text
 */
export function getTextDirection(text: string): 'rtl' | 'ltr' {
  const rtlChars = /[\u0590-\u083F\u08A0-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]/;
  const ltrChars = /[a-zA-Z]/;
  
  const rtlCount = (text.match(rtlChars) || []).length;
  const ltrCount = (text.match(ltrChars) || []).length;
  
  return rtlCount > ltrCount ? 'rtl' : 'ltr';
}

/**
 * Clean and normalize Persian text
 */
export function normalizePersianText(text: string): string {
  return text
    // Normalize Persian/Arabic characters
    .replace(/ي/g, 'ی')
    .replace(/ك/g, 'ک')
    .replace(/ؤ/g, 'و')
    .replace(/إ|أ/g, 'ا')
    // Remove extra whitespace
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Legal term translator (Persian to English and vice versa)
 */
export const legalTerms = {
  // Court terms
  'دادگاه': 'court',
  'قاضی': 'judge',
  'وکیل': 'lawyer',
  'دادستان': 'prosecutor',
  'شاکی': 'plaintiff',
  'متهم': 'defendant',
  'شاهد': 'witness',
  
  // Legal documents
  'حکم': 'verdict',
  'رأی': 'judgment',
  'دادنامه': 'court_decision',
  'لایحه': 'lawsuit',
  'اعتراض': 'objection',
  'تجدیدنظر': 'appeal',
  
  // Legal processes
  'محاکمه': 'trial',
  'جلسه': 'session',
  'اجرا': 'execution',
  'تحقیقات': 'investigation',
  'بازجویی': 'interrogation',
  
  // Legal status
  'نهایی': 'final',
  'قطعی': 'definitive',
  'موقت': 'temporary',
  'معلق': 'suspended',
};

/**
 * Translate legal terms
 */
export function translateLegalTerm(
  term: string, 
  direction: 'fa-to-en' | 'en-to-fa' = 'fa-to-en'
): string {
  if (direction === 'fa-to-en') {
    return legalTerms[term as keyof typeof legalTerms] || term;
  } else {
    const reversed = Object.fromEntries(
      Object.entries(legalTerms).map(([fa, en]) => [en, fa])
    );
    return reversed[term] || term;
  }
}

/**
 * Extract Persian legal entities from text
 */
export function extractLegalEntities(text: string): {
  courts: string[];
  judges: string[];
  lawyers: string[];
  cases: string[];
} {
  const entities = {
    courts: [] as string[],
    judges: [] as string[],
    lawyers: [] as string[],
    cases: [] as string[],
  };

  // Court patterns
  const courtPatterns = [
    /دادگاه\s+[^\s]+/g,
    /شعبه\s+\d+\s+دادگاه/g,
    /دیوان\s+[^\s]+/g,
  ];

  courtPatterns.forEach(pattern => {
    const matches = text.match(pattern);
    if (matches) {
      entities.courts.push(...matches);
    }
  });

  // Judge patterns
  const judgePatterns = [
    /جناب\s+آقای\s+[^\s]+/g,
    /سرکار\s+خانم\s+[^\s]+/g,
    /قاضی\s+[^\s]+/g,
  ];

  judgePatterns.forEach(pattern => {
    const matches = text.match(pattern);
    if (matches) {
      entities.judges.push(...matches);
    }
  });

  // Case number patterns
  const casePatterns = [
    /شماره\s+\d+\/\d+\/\d+/g,
    /کلاسه\s+\d+/g,
  ];

  casePatterns.forEach(pattern => {
    const matches = text.match(pattern);
    if (matches) {
      entities.cases.push(...matches);
    }
  });

  return entities;
}

/**
 * Persian keyboard layout utilities
 */
export const persianKeyboard = {
  /**
   * Convert QWERTY to Persian layout
   */
  qwertyToPersian: (text: string): string => {
    const qwertyToPersianMap: Record<string, string> = {
      'q': 'ض', 'w': 'ص', 'e': 'ث', 'r': 'ق', 't': 'ف', 'y': 'غ', 'u': 'ع', 'i': 'ه', 'o': 'خ', 'p': 'ح',
      'a': 'ش', 's': 'س', 'd': 'ی', 'f': 'ب', 'g': 'ل', 'h': 'ا', 'j': 'ت', 'k': 'ن', 'l': 'م', ';': 'ک',
      'z': 'ظ', 'x': 'ط', 'c': 'ز', 'v': 'ر', 'b': 'ذ', 'n': 'د', 'm': 'پ', ',': 'و', '.': '.',
    };

    return text.toLowerCase().split('').map(char => 
      qwertyToPersianMap[char] || char
    ).join('');
  },

  /**
   * Auto-detect and convert mixed keyboard input
   */
  autoCorrectKeyboard: (text: string): string => {
    // Simple heuristic: if text contains English letters but seems like Persian words
    const hasEnglishLetters = /[a-zA-Z]/.test(text);
    const hasPersianLetters = /[\u0600-\u06FF]/.test(text);
    
    if (hasEnglishLetters && !hasPersianLetters) {
      // Likely mixed keyboard input
      return persianKeyboard.qwertyToPersian(text);
    }
    
    return text;
  },
};

/**
 * RTL-aware CSS class helper
 */
export function rtlClass(ltrClass: string, rtlClass: string, text?: string): string {
  if (text) {
    return getTextDirection(text) === 'rtl' ? rtlClass : ltrClass;
  }
  
  // Default to RTL for Persian interface
  return rtlClass;
}

/**
 * Format file size in Persian
 */
export function formatPersianFileSize(bytes: number): string {
  const units = ['بایت', 'کیلوبایت', 'مگابایت', 'گیگابایت'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  const formattedSize = size < 10 ? size.toFixed(1) : Math.round(size);
  return `${toPersianNumbers(formattedSize)} ${units[unitIndex]}`;
}