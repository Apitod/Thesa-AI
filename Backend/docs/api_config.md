# API Configuration Guide

## Masalah API yang Terjadi

### Error Status: 404 → 401
- **404 Not Found**: URL API `https://api.z.ai/v1/chat/completions` tidak valid
- **401 Authentication**: API Key tidak valid untuk OpenAI

### Analisis
Format API key Anda: `7477960d5df54580a5a6434e4a8cb856.bJXubdJe92IU6vIB`
- Bukan format OpenAI standar (biasanya mulai dengan `sk-`)

---

## Solusi yang Tersedia

### 1. Ganti dengan API Key yang Valid

#### OpenAI API
Jika ingin menggunakan OpenAI:
1. Dapatkan API key dari https://platform.openai.com/api-keys
2. Format: `sk-proj-...`
3. Set di .env:
```env
ZAI_API_KEY=sk-proj-xxxxxxxxxxxxx
ZAI_API_URL=https://api.openai.com/v1/chat/completions
```

#### OpenRouter (Multi-Provider)
Jika ingin provider lain:
1. Dapatkan API key dari https://openrouter.ai/keys
2. Set di .env:
```env
ZAI_API_KEY=sk-or-v1-xxxxxxxxxxxxx
ZAI_API_URL=https://openrouter.ai/api/v1/chat/completions
```

### 2. Gunakan Mode Manual (Tanpa API)

Ini adalah cara termudah dan gratis:

**Cara menjalankan:**
```bash
python src/main.py
```

**Pilih opsi:**
- Pilih mode "1 (Manual)"
- Isi semua konten secara manual
- Tidak membutuhkan API key
- Tidak membutuhkan koneksi internet
- Gratis sepenuhnya

### 3. Dapatkan API Key Gratis

Beberapa provider menawarkan free tier:

#### Anthropic Claude
- Website: https://console.anthropic.com/
- Free tier tersedia

#### Together AI
- Website: https://together.ai/
- Free tier untuk testing

#### Groq
- Website: https://console.groq.com/
- Gratis untuk penggunaan personal

---

## Rekomendasi Cepat

### Opsi 1: Gunakan Mode Manual (Segera)
```bash
# Jalankan sekarang, tanpa perlu setup
python src/main.py

# Pilih mode 1 (Manual)
# Isi konten sesuai kebutuhan
```

### Opsi 2: Dapatkan API Key Gratis (5 menit)
```bash
# 1. Daftar di salah satu provider:
#    - https://console.anthropic.com/
#    - https://together.ai/
#    - https://console.groq.com/

# 2. Copy API key yang didapat

# 3. Update file .env:
ZAI_API_KEY=sk-ant-xxxxxxxxxxxxx  # ganti dengan key Anda
ZAI_API_URL=https://api.anthropic.com/v1/messages  # sesuaikan dengan provider
```

---

## Testing API Connection

Gunakan test script untuk verifikasi:
```bash
python test_api.py
```

---

## Daftar API Endpoint Populer

```env
# OpenAI
ZAI_API_URL=https://api.openai.com/v1/chat/completions

# Anthropic Claude
ZAI_API_URL=https://api.anthropic.com/v1/messages

# OpenRouter (multi-provider)
ZAI_API_URL=https://openrouter.ai/api/v1/chat/completions

# Together AI
ZAI_API_URL=https://api.together.xyz/v1/chat/completions

# Groq (fast)
ZAI_API_URL=https://api.groq.com/openai/v1/chat/completions
```

---

## Catatan Penting

1. **API Key Confidential**: Jangan share API key Anda ke publik
2. **Usage Limits**: Perhatikan batas penggunaan free tier
3. **Cost Control**: Monitor penggunaan token di logs/token_usage.json
4. **Fallback**: Jika API tidak berfungsi, gunakan mode manual

---

## Status Sistem Saat Ini

✅ Sistem: READY FOR USE
✅ Mode Manual: BERFUNGSI
❌ Mode AI: BUTUH API KEY YANG VALID

**Sistem tetap dapat digunakan sepenuhnya dengan mode manual!**