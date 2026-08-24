export type Language = {
  code: string;
  name: string;
  flag: string;
  rtl?: boolean;
};

export const languages: Language[] = [
  { code: "en", name: "English", flag: "🇬🇧" },
  { code: "ar", name: "العربية · Arabic", flag: "🇦🇪", rtl: true },
  { code: "af", name: "Afrikaans", flag: "🇿🇦" },
  { code: "sq", name: "Shqip · Albanian", flag: "🇦🇱" },
  { code: "am", name: "አማርኛ · Amharic", flag: "🇪🇹" },
  { code: "hy", name: "Հայերեն · Armenian", flag: "🇦🇲" },
  { code: "az", name: "Azərbaycan · Azerbaijani", flag: "🇦🇿" },
  { code: "bn", name: "বাংলা · Bengali", flag: "🇧🇩" },
  { code: "bs", name: "Bosanski · Bosnian", flag: "🇧🇦" },
  { code: "bg", name: "Български · Bulgarian", flag: "🇧🇬" },
  { code: "my", name: "မြန်မာ · Burmese", flag: "🇲🇲" },
  { code: "ca", name: "Català · Catalan", flag: "🇪🇸" },
  { code: "zh", name: "中文 · Chinese", flag: "🇨🇳" },
  { code: "hr", name: "Hrvatski · Croatian", flag: "🇭🇷" },
  { code: "cs", name: "Čeština · Czech", flag: "🇨🇿" },
  { code: "da", name: "Dansk · Danish", flag: "🇩🇰" },
  { code: "nl", name: "Nederlands · Dutch", flag: "🇳🇱" },
  { code: "et", name: "Eesti · Estonian", flag: "🇪🇪" },
  { code: "fi", name: "Suomi · Finnish", flag: "🇫🇮" },
  { code: "fr", name: "Français · French", flag: "🇫🇷" },
  { code: "ka", name: "ქართული · Georgian", flag: "🇬🇪" },
  { code: "de", name: "Deutsch · German", flag: "🇩🇪" },
  { code: "el", name: "Ελληνικά · Greek", flag: "🇬🇷" },
  { code: "gu", name: "ગુજરાતી · Gujarati", flag: "🇮🇳" },
  { code: "he", name: "עברית · Hebrew", flag: "🇮🇱", rtl: true },
  { code: "hi", name: "हिन्दी · Hindi", flag: "🇮🇳" },
  { code: "hu", name: "Magyar · Hungarian", flag: "🇭🇺" },
  { code: "is", name: "Íslenska · Icelandic", flag: "🇮🇸" },
  { code: "id", name: "Bahasa Indonesia", flag: "🇮🇩" },
  { code: "ga", name: "Gaeilge · Irish", flag: "🇮🇪" },
  { code: "it", name: "Italiano · Italian", flag: "🇮🇹" },
  { code: "ja", name: "日本語 · Japanese", flag: "🇯🇵" },
  { code: "kn", name: "ಕನ್ನಡ · Kannada", flag: "🇮🇳" },
  { code: "kk", name: "Қазақша · Kazakh", flag: "🇰🇿" },
  { code: "km", name: "ខ្មែរ · Khmer", flag: "🇰🇭" },
  { code: "ko", name: "한국어 · Korean", flag: "🇰🇷" },
  { code: "lo", name: "ລາວ · Lao", flag: "🇱🇦" },
  { code: "lv", name: "Latviešu · Latvian", flag: "🇱🇻" },
  { code: "lt", name: "Lietuvių · Lithuanian", flag: "🇱🇹" },
  { code: "ms", name: "Bahasa Melayu", flag: "🇲🇾" },
  { code: "ml", name: "മലയാളം · Malayalam", flag: "🇮🇳" },
  { code: "mr", name: "मराठी · Marathi", flag: "🇮🇳" },
  { code: "mn", name: "Монгол · Mongolian", flag: "🇲🇳" },
  { code: "ne", name: "नेपाली · Nepali", flag: "🇳🇵" },
  { code: "no", name: "Norsk · Norwegian", flag: "🇳🇴" },
  { code: "fa", name: "فارسی · Persian", flag: "🇮🇷", rtl: true },
  { code: "pl", name: "Polski · Polish", flag: "🇵🇱" },
  { code: "pt", name: "Português · Portuguese", flag: "🇵🇹" },
  { code: "pa", name: "ਪੰਜਾਬੀ · Punjabi", flag: "🇮🇳" },
  { code: "ro", name: "Română · Romanian", flag: "🇷🇴" },
  { code: "ru", name: "Русский · Russian", flag: "🇷🇺" },
  { code: "sr", name: "Српски · Serbian", flag: "🇷🇸" },
  { code: "sk", name: "Slovenčina · Slovak", flag: "🇸🇰" },
  { code: "sl", name: "Slovenščina · Slovenian", flag: "🇸🇮" },
  { code: "so", name: "Soomaali · Somali", flag: "🇸🇴" },
  { code: "es", name: "Español · Spanish", flag: "🇪🇸" },
  { code: "sw", name: "Kiswahili · Swahili", flag: "🇰🇪" },
  { code: "sv", name: "Svenska · Swedish", flag: "🇸🇪" },
  { code: "ta", name: "தமிழ் · Tamil", flag: "🇮🇳" },
  { code: "te", name: "తెలుగు · Telugu", flag: "🇮🇳" },
  { code: "th", name: "ไทย · Thai", flag: "🇹🇭" },
  { code: "tr", name: "Türkçe · Turkish", flag: "🇹🇷" },
  { code: "uk", name: "Українська · Ukrainian", flag: "🇺🇦" },
  { code: "ur", name: "اردو · Urdu", flag: "🇵🇰", rtl: true },
  { code: "uz", name: "O‘zbek · Uzbek", flag: "🇺🇿" },
  { code: "vi", name: "Tiếng Việt · Vietnamese", flag: "🇻🇳" },
  { code: "cy", name: "Cymraeg · Welsh", flag: "🇬🇧" },
];

export const defaultLanguage = languages[0];

export function languageByCode(code: string): Language {
  return (
    languages.find((language) => language.code === code) ?? defaultLanguage
  );
}
