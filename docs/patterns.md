# Pola dari sumber luar (dan apa yang diambil)

Semua tautan diperiksa bisa dibuka saat disusun (26 Oktober 2026). Repo diperiksa lewat
GitHub API (bintang, update terakhir, status arsip).

## Konteks & sesi panjang

- Anthropic — **Effective context engineering for AI agents**
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
  Ambil: konteks yang menua menurunkan mutu; obatnya compaction, catatan terstruktur,
  dan pemisahan konteks ke sub-agen.
- Anthropic — **Building effective agents**
  https://www.anthropic.com/engineering/building-effective-agents
  Ambil: loop agen wajib punya kondisi berhenti eksplisit.
- Anthropic — **Multi-agent research system**
  https://www.anthropic.com/engineering/multi-agent-research-system
  Ambil: sub-agen mengisolasi konteks; sistem banyak agen memakai ±15x token.
- Manus — **Context engineering**
  https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
  Ambil: tulis ulang daftar tugas (recitation) supaya rencana tidak terlupa; biarkan galat
  tampil; jangan tambah konteks tanpa alasan.
- Cognition — **Don't build multi-agents**
  https://cognition.ai/blog/dont-build-multi-agents
  Ambil: pemisahan agen tanpa konteks bersama memecah keputusan implisit.
- arXiv 2505.06120 — **LLMs Get Lost In Multi-Turn Conversation** https://arxiv.org/abs/2505.06120
  Ambil: mutu turun ±39% di percakapan banyak putaran vs satu putaran.
- arXiv 2411.07037 — **LIFBench** https://arxiv.org/abs/2411.07037
  Ambil: kepatuhan instruksi terukur menurun pada konteks panjang.

## Penegakan, batas, dan penjaga

- OpenAI — **A practical guide to building agents** (PDF)
  https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
  Ambil: kondisi keluar + batas langkah + guardrail sebagai tiga hal terpisah.
- HumanLayer — **12-Factor Agents**
  https://github.com/humanlayer/12-factor-agents
  Ambil: faktor "own your context window" dan "control flow"; agen fokus, bukan serbaguna.
- LangChain — **Context engineering for agents**
  https://blog.langchain.com/context-engineering-for-agents/
  Ambil: empat cara menangani konteks: tulis, pilih, ringkas, pisah.
- Resilience4j (circuit breaker) https://github.com/resilience4j/resilience4j
  Ambil: status breaker CLOSED → OPEN → HALF_OPEN, bukan retry tak terbatas.
- Temporal https://github.com/temporalio/temporal · Restate https://github.com/restatedev/restate ·
  pgmq https://github.com/pgmq/pgmq · BullMQ https://github.com/taskforcesh/bullmq
  Ambil: klaim kerja atomik (`FOR UPDATE SKIP LOCKED`), lease berbatas waktu (`visibility_timeout`,
  `acks_late`), dan pemulihan pekerja mati oleh reaper.
- Redisson https://github.com/redisson/redisson — watchdog yang memperpanjang lease otomatis.
  Ambil: lease harus diperpanjang pekerja hidup dan kedaluwarsa sendiri saat pekerja mati.

## Yang tidak diambil

- Framework lengkap (Temporal/Restate/LangGraph) untuk kebutuhan sekecil ini — menambah
  layanan yang harus dijaga. Polanya diambil, layanannya tidak.
- Membunuh pekerja otomatis karena pola melenceng — salah tuduh mahal.
- Menambah agen paralel sebagai obat kelambatan — biaya naik lebih cepat daripada hasil.

## Anti-pola yang kami hindari

Status `running` tanpa lease dan tanpa pemilik; kunci tanpa batas waktu; menugaskan ulang
brief identik tanpa batas; pemeriksa yang konteksnya tidak terpisah dari pembuat; retry
tanpa mundur; mengakui tugas selesai sebelum ada bukti.
