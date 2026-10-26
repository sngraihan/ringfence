# Aturan wajib di setiap brief pekerja (template)

Tempelkan blok ini ke setiap tugas. Isi khusus tugas ditulis di atasnya; aturan ini
tidak boleh dilupakan karena brief cepat tenggelam di sesi panjang.

```
ATURAN EFISIENSI WAJIB
1. BATCH temuan: bereskan SEMUA temuan di brief/probe dalam SATU putaran + SATU commit.
   Dilarang menambal satu per satu lalu membuka putaran verifikasi baru.
2. Test fokus saat iterasi. Uji penuh SEKALI pada kandidat beku sebelum serah terima.
3. Dilarang menunggu dengan jeda berulang (sleep-poll). Jalankan perintah secara
   blocking, baca hasilnya sekali.
4. Jangan membaca ulang file/log yang sudah dibaca. Jangan menjelajah di luar file
   yang disebut brief.
5. Jangan menjalankan ulang perintah dengan kode sumber + perintah identik.
6. RECITATION: setiap ~5 langkah tulis ulang PROGRESS.md (selesai / berikutnya /
   larangan yang masih berlaku), lalu baca ulang.
7. Zona handoff: di 60 langkah tanpa kemajuan, BERHENTI dan tulis handoff ringkas ke
   PROGRESS.md + kirim laporan. Batas keras 80 langkah; sesi berikutnya lanjut dari
   PROGRESS.md, bukan mengulang.
8. Berhenti begitu uji terdampak + bukti lulus. Tidak ada audit tambahan tanpa alasan
   tertulis.
9. Jangan menghapus pemeriksaan mutu demi cepat. Yang dipangkas hanya pengulangan.
```

## Kenapa ditulis eksplisit

Aturan di tempat lain (skill, brief) hilang pengaruhnya di sesi panjang. Blok ini
dipasang DUA kali: di brief, dan di pengirim kerja (`should_stop()` dan handoff).
Yang kedua tidak bisa dilupakan.
