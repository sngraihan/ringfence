# Sumber pola & lisensi

Kami mengamati repo-repo ini lebih dulu, lalu meniru **pola**-nya (bukan menyalin
kode asing ke sini). Kalau di kemudian hari ada kode yang disalin, notice pemilik
aslinya wajib dibawa.

| Repo | Lisensi | Yang diambil |
|---|---|---|
| [a5c-ai/babysitter](https://github.com/a5c-ai/babysitter) | MIT | Jurnal peristiwa append-only (satu peristiwa = satu berkas, tulis atomic) + status dibangun ulang dengan membaca ulang jurnal; penanda idempotensi ber-hash (`sha256`) alih-alih bendera; presedensi aturan deny > warn > allow sebagai fungsi murni `evaluate()` + jejak keputusan. |
| [GammaLabTechnologies/harmonist](https://github.com/GammaLabTechnologies/harmonist) | MIT | Kontrak brief: baris pertama wajib `AGENT:`/`OWNER:` dan panjang minimum, kalau tidak ditolak; `stop` dengan `loop_limit`; panggilan terbuka yang lebih tua dari ambang (default 900 detik) dianggap selesai supaya pekerja mati tidak menggantung. |
| [VicKayro/leash](https://github.com/VicKayro/leash) | MIT | Deteksi putaran dari hash `tool + input`: ambang 10x total atau 6x dalam 10 menit; dedup catatan biaya; pagar belanja harian/per-jam yang fail-open. |
| [omnigent-ai/omnigent](https://github.com/omnigent-ai/omnigent) | Apache-2.0 | Keputusan berlapis ALLOW/DENY/ASK pada fase permintaan dan pemanggilan alat; batas jumlah pemanggilan alat per sesi sebagai proksi "kebanyakan langkah". |
| [resilience4j](https://github.com/resilience4j/resilience4j) | Apache-2.0 | Status pemutus sirkuit CLOSED → OPEN → HALF_OPEN, bukan percobaan ulang tanpa batas. |

Sumber tulisan (bukan kode) ada di [`patterns.md`](patterns.md).

Catatan tanggung jawab: repo di atas jauh lebih besar dan lebih lengkap dari Ringfence.
Kalau kebutuhanmu besar (orkestrasi banyak agen, dashboard, workflow tahan lama),
pakai repo di atas — bukan ini.
