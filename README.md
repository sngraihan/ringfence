# Ringfence

Guard layer kecil untuk pekerja AI yang jalan lama: supaya tidak mengulang pekerjaan
yang sudah selesai, tidak dua pekerja di direktori yang sama, tidak berputar sampai
kehabisan langkah, dan tidak melenceng dari tugasnya.

Hanya bergantung pada pustaka standar Python 3.11+. Tanpa server, tanpa queue, tanpa
basis data. Menempel pada pengirim kerja yang sudah ada (di kami: papan tugas kanban).

## Status jujur

Dipakai di kantor internal kami sejak 26 Oktober 2026. **Belum diuji luas di luar itu.**
Isi repo ini hasil dari insiden nyata, dan akan berubah seiring pemakaian. Kalau kamu
mencari framework lengkap, ini bukan itu.

## Masalah yang diselesaikan (semuanya pernah terjadi)

| Kejadian nyata | Akibat | Penjaga |
|---|---|---|
| Pekerjaan 250 langkah untuk perbaikan 1 baris kode | 548 pemanggilan alat, biaya membengkak, hasil tetap terpotong | `should_stop()` |
| Kartu yang sudah selesai dijalankan ulang oleh pengirim kerja | pekerjaan ganda, hasil yang sedang diperiksa berubah | `completion()` / `mark_done()` |
| Dua pekerja di direktori yang sama | pemeriksa menilai hasil yang sudah bergeser | `WorkLock` |
| Pekerja menunggu job dengan jeda berulang (`sleep 45` x puluhan) | token terbakar per putaran tanpa kemajuan | `detect_drift()` |
| Pekerja memeriksa kredensial/infra padahal tugasnya mengukur halaman | 15 menit hilang, tidak ada hasil | `detect_drift()` |

## Isi

```python
from ringfence import WorkLock, completion, mark_done, detect_drift, should_stop

# 1. satu direktori = satu pekerja
lock = WorkLock("/srv/work/task-42", owner="builder", ttl=1800)
if not lock.acquire():
    raise SystemExit("direktori masih dipakai pekerja lain")

# 2. kerja selesai tidak dijalankan ulang
if (c := completion("/srv/work/task-42")) and c["rc"] == 0:
    raise SystemExit("sudah selesai, tunggu pemeriksa")

# 3. batas langkah/waktu + zona handoff sebelum batas keras
stop, why = should_stop(turns=61, seconds=300, max_turns=80, max_seconds=2400)
if stop:
    write_progress_note(why)   # tutup dengan catatan, lanjut di sesi baru

# 4. pola buruk di catatan kerja -> tahan untuk diperiksa, bukan bunuh otomatis
drift = detect_drift(open("worker.log").read(), task_title="gate tampilan halaman")
```

## Aturan yang menyertai penjaga

Penjaga teknis saja tidak cukup kalau aturan kerja tidak ditulis. Template aturan yang
kami tempelkan ke setiap brief pekerja: [`rules/BRIEF_RULES.md`](rules/BRIEF_RULES.md).

Tiga yang paling berdampak:
1. **Batalkan pengulangan** — semua temuan dibereskan dalam satu putaran, satu commit.
2. **Recitation** — pekerja menulis ulang catatan progres tiap ~5 langkah lalu membacanya.
   Aturan di brief cepat terlupa di sesi panjang; menulis ulang lebih kuat daripada mengingat.
3. **Handoff, bukan melanjutkan** — di 60 langkah tanpa kemajuan, berhenti dan serahkan
   catatan; sesi berikutnya lanjut dari catatan itu, bukan mengulang dari awal.

## Yang TIDAK dianjurkan (dan alasannya)

- **Membunuh pekerja otomatis karena dicurigai melenceng.** Salah tuduh itu mahal.
  `detect_drift()` melaporkan; keputusan menghentikan ada di pengawas.
- **Menaikkan batas langkah supaya pekerjaan "selesai".** Sesi kepanjangan justru
  menurunkan kepatuhan; lebih baik dipecah dengan serah terima catatan.
- **Menambah banyak agen paralel.** Menambah jumlah agen menambah biaya jauh lebih
  cepat daripada menambah hasil.

## Sudah ada yang bikin?

Ya, ada yang berdekatan — kami cek dulu sebelum menulis ini:

- [a5c-ai/babysitter](https://github.com/a5c-ai/babysitter) — memaksa kepatuhan aturan pada
  kumpulan agen.
- [GammaLabTechnologies/harmonist](https://github.com/GammaLabTechnologies/harmonist) —
  orkestrasi agen dengan penegakan protokol mekanis.
- [VicKayro/leash](https://github.com/VicKayro/leash) — melihat biaya, loop, dan cron mati
  milik agen.
- [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent) — meta-harness orkestrasi.

Ringfence lebih kecil dan lebih sempit: tiga penjaga + aturan brief, tanpa framework,
tanpa layanan. Kalau kebutuhanmu besar, pakai yang di atas.

## Dasar dari sumber luar

Ringkasan sumber (Anthropic, Cognition, Manus, OpenAI, arXiv) dan apa yang diambil
dari masing-masing: [`docs/patterns.md`](docs/patterns.md).
Catatan insiden mentah sebagai bukti: [`docs/incidents.md`](docs/incidents.md).

## Uji

```bash
python3 tests/test_guard.py
```

## Lisensi

MIT — lihat [LICENSE](LICENSE).
