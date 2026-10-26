# Catatan insiden (bukti asal-usul)

Tanggal 26 Oktober 2026, satu kantor dengan papan tugas kanban, beberapa pekerja AI
per profil. Semua angka di bawah dari log dan basis data papan, bukan perkiraan.

## 1. Perbaikan 1 baris, 250 langkah

Perbaikan jalur uang langganan bulanan = satu baris kode (`summary.ModelQuota = tieredQuota`)
di `service/text_quota.go`. Yang terjadi:

- enam kali uji matriks penuh 3 basis data dalam sehari (11:12, 11:14, 11:19, 12:37, 12:37, 14:02),
  karena temuan pemeriksa keluar satu per satu di akhir tiap putaran.
- satu run pekerja lain: `Duration 25m43s`, `Messages 551 (548 tool call)`, berakhir
  `Iteration budget reached (250/250) — response may be incomplete`.

Pelajaran: temuan harus dibatch dalam satu putaran, dan batas langkah harus jauh di bawah
titik di mana hasil justru terpotong.

## 2. Pekerjaan selesai dijalankan ulang

Kartu `t_c47ba9ce` sudah selesai: log runner berakhir `rc=0`, commit ada, laporan ada.
Pengirim kerja tetap menjalankannya lagi 1 menit kemudian karena kartu masih berstatus
`running` dan penanda "sudah selesai" tidak dikenali. Run kedua sudah mulai membaca ulang
sumber dan menjalankan perintah lagi, sementara pemeriksa sedang menilai commit yang sama.

Pelajaran: "log berakhir rc=0" harus jadi penanda keras yang mencegah penugasan ulang,
bukan disimpulkan dari status papan.

## 3. Dua pekerja, satu direktori

Di tengah insiden (2), pemeriksa independen sedang membaca commit `b695c80` di direktori
yang sama yang dipakai pekerja kedua. Hasil apa pun dari pemeriksa itu bisa menunjuk
kode yang sudah berubah.

Pelajaran: satu direktori = satu pekerja, ditegakkan dengan lease, bukan dengan ingatan.

## 4. Menunggu dengan jeda berulang

Satu pemeriksaan tampilan berjalan 22-28 menit dengan pola `sleep 45` / `sleep 50` /
`sleep 55` berulang, lalu mulai memeriksa `docker images` dan `docker inspect postgres`
di luar cakupan tugasnya, sementara laporan akhirnya masih 117 byte.

Pelajaran: menunggu dengan jeda mengubah satu pekerjaan jadi puluhan pemanggilan model.
Yang bekerja: satu perintah blocking dengan batas waktu panjang, baca hasil sekali.

## 5. Efek samping yang tidak diinginkan

Kami sempat membangun sensor yang membunuh pekerja begitu terlihat pola melenceng.
Riset menunjukkan itu anti-pola: salah tuduh mahal, dan pekerja yang dihentikan di tengah
sering kehilangan bukti. Sekarang sensor hanya menahan dan melaporkan; keputusan
menghentikan ada di pengawas.

## Selisih setelah penjaga dipasang

Pemeriksaan uang yang sama, dijalankan ulang dengan aturan baru: **3 menit 17 detik, 28
pemanggilan alat, putusan lengkap** — dibanding 28 menit tanpa putusan pada percobaan
sebelumnya.
