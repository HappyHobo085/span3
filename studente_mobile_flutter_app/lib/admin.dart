import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:nfc_manager/nfc_manager.dart';

// Data class — unchanged.
class _AdminKlasRy {
  final int lokasieId;
  final String kampusNaam;
  final String klasNaam;
  final String beskrywing;
  final String? nfcUid;

  _AdminKlasRy({
    required this.lokasieId,
    required this.kampusNaam,
    required this.klasNaam,
    required this.beskrywing,
    this.nfcUid,
  });
}

class AdminHomePage extends StatefulWidget {
  const AdminHomePage({super.key});

  @override
  State<AdminHomePage> createState() => _AdminHomePageState();
}

class _AdminHomePageState extends State<AdminHomePage> {
  final List<_AdminKlasRy> _rye = [];
  int? _gekoseLokasieId;
  bool _laai = true;
  String? _fout;
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    _herlaai();
  }

  // Fetch logic — unchanged.
  Future<void> _herlaai() async {
    setState(() { _laai = true; _fout = null; });
    try {
      final kampusse = await MoonApi.fetchKampusse();
      final lokasies = await MoonApi.fetchLokasies();
      final idNaKampus = {for (final k in kampusse) k.kampusId: k.naam};
      if (!mounted) return;
      setState(() {
        _rye
          ..clear()
          ..addAll(lokasies.map((l) => _AdminKlasRy(
                lokasieId: l.id,
                kampusNaam: l.kampusId != null
                    ? (idNaKampus[l.kampusId!] ?? 'Kampus #${l.kampusId}')
                    : '—',
                klasNaam: l.naam.trim().isNotEmpty ? l.naam.trim() : '—',
                beskrywing: l.beskrywing?.trim().isNotEmpty == true
                    ? l.beskrywing!.trim()
                    : '—',
                nfcUid: l.nfcUid,
              )));
        _gekoseLokasieId = null;
        _laai = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() { _fout = e.toString(); _laai = false; });
    }
  }

  // NFC write logic — unchanged.
  Future<void> _skryfUid() async {
  final id = _gekoseLokasieId;

  if (id == null) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text("Kies eers 'n klas in die lys.")),
    );
    return;
  }

  final gekoseKlas = _rye.firstWhere(
    (r) => r.lokasieId == id,
  );

  final uid = gekoseKlas.nfcUid;

  if (uid == null || uid.trim().isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '${gekoseKlas.klasNaam} het nog geen UID nie. Herlaai klasse of wag vir server rebuild.',
        ),
      ),
    );
    return;
  }

  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      backgroundColor: kBg,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: kBorderEm, width: 1),
      ),
      title: Text(
        'Skryf NFC tag',
        style: GoogleFonts.inter(
          color: kText1,
          fontSize: 16,
          fontWeight: FontWeight.w700,
        ),
      ),
      content: Text(
        'Hou die NFC tag teen die toestel.\n\n'
        'Klas: ${gekoseKlas.klasNaam}\n'
        'UID: $uid',
        style: GoogleFonts.inter(
          color: kText2,
          fontSize: 13,
        ),
      ),
      actions: [
        OutlineActionButton(
          label: 'Kanselleer',
          onTap: () => Navigator.pop(ctx, false),
          height: 40,
          width: 110,
        ),
        const SizedBox(width: 8),
        GradientActionButton(
          label: 'Skryf',
          onTap: () => Navigator.pop(ctx, true),
          height: 40,
          width: 90,
        ),
      ],
      actionsPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    ),
  );

  if (ok != true) return;

  try {
    await NfcManager.instance.startSession(
      onDiscovered: (tag) async {
        final ndef = Ndef.from(tag);

        if (ndef == null || !ndef.isWritable) {
          await NfcManager.instance.stopSession(
            errorMessage: 'Tag is nie skryfbaar nie.',
          );
          return;
        }

        final record = NdefRecord.createText(uid);
        final message = NdefMessage([record]);

        await ndef.write(message);
        await NfcManager.instance.stopSession();

        if (!mounted) return;

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            backgroundColor: Colors.green,
            content: Text(
              'NFC tag suksesvol geskryf.',
              style: TextStyle(color: Colors.white),
            ),
          ),
        );
      },
    );
  } catch (e) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: Colors.red,
        content: Text(
          'Fout: $e',
          style: const TextStyle(color: Colors.white),
        ),
      ),
    );
  }
}

  void _onNavTap(int index) {
    setState(() => _selectedIndex = index);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 10),
            Expanded(
              child: _selectedIndex == 0
                  ? _TuisTab(rye: _rye, laai: _laai, fout: _fout)
                  : _selectedIndex == 1
                      ? _KlasseTab(
                          rye: _rye,
                          laai: _laai,
                          fout: _fout,
                          gekoseLokasieId: _gekoseLokasieId,
                          onKies: (id) =>
                              setState(() => _gekoseLokasieId = id),
                        )
                      : _selectedIndex == 2
                          ? _NfcTab(
                              gekoseLokasieId: _gekoseLokasieId,
                              onSkryf: _skryfUid,
                              onHerlaai: _herlaai,
                            )
                          : const _ProfielTab(),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _AdminNavBar(
        selectedIndex: _selectedIndex,
        onTap: _onNavTap,
      ),
    );
  }
}

// ─── Tuis tab ─────────────────────────────────────────────────────────────────
class _TuisTab extends StatelessWidget {
  final List<_AdminKlasRy> rye;
  final bool laai;
  final String? fout;

  const _TuisTab({required this.rye, required this.laai, required this.fout});

  @override
  Widget build(BuildContext context) {
    final kampusCount = rye.map((r) => r.kampusNaam).toSet().length;

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.only(bottom: 20),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Tuis',
                        style: GoogleFonts.inter(
                          color: kText1,
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Admin',
                        style: GoogleFonts.inter(
                            color: kTextMuted, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: kSurface1,
                    border: Border.all(color: kBorder, width: 1.5),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.notifications_outlined,
                      color: kTextMuted, size: 18),
                ),
              ],
            ),
          ),

          // Stat cards
          Row(
            children: [
              Expanded(
                child: _StatCard(
                  label: 'KLASSE',
                  value: laai ? '—' : '${rye.length}',
                  valueColor: kText1,
                  badge: '♦ Gelys',
                  badgeColor: kSuccess,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StatCard(
                  label: 'KAMPUSSE',
                  value: laai ? '—' : '$kampusCount',
                  valueColor: kAccent2,
                  badge: '♦ Aktief',
                  badgeColor: kAccent2,
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // NFC summary card
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
            decoration: kGlassDecoration(
                radius: 14, borderColor: const Color(0x737B61FF)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'NFC BESTUUR',
                  style: GoogleFonts.inter(
                    color: kTextMuted,
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    const Icon(Icons.nfc, color: kAccent, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Kies \'n klas en skryf \'n NFC tag',
                        style: GoogleFonts.inter(
                          color: kText2,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Klasse tab ───────────────────────────────────────────────────────────────
class _KlasseTab extends StatelessWidget {
  final List<_AdminKlasRy> rye;
  final bool laai;
  final String? fout;
  final int? gekoseLokasieId;
  final ValueChanged<int> onKies;

  const _KlasseTab({
    required this.rye,
    required this.laai,
    required this.fout,
    required this.gekoseLokasieId,
    required this.onKies,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Klasse',
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.refresh, color: kAccent),
                onPressed: () {
                  // call _herlaai()
                },
              ),
            ],
          ),
          Expanded(
            child: GlassCard(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'KLASSE',
                    style: GoogleFonts.inter(
                      color: kTextMuted,
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.5,
                    ),
                  ),
                  const SizedBox(height: 10),
                  if (laai)
                    const Center(
                        child: CircularProgressIndicator(color: kAccent))
                  else if (fout != null)
                    Text(fout!,
                        style: GoogleFonts.inter(
                            color: const Color(0xFFEF4444), fontSize: 12))
                  else
                    Expanded(
                      child: ListView.separated(
                        itemCount: rye.length,
                        separatorBuilder: (_, __) =>
                            const Divider(color: Color(0x0AFFFFFF), height: 1),
                        itemBuilder: (_, i) {
                          final r = rye[i];
                          final selected = gekoseLokasieId == r.lokasieId;
                          return GestureDetector(
                            onTap: () => onKies(r.lokasieId),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  vertical: 8, horizontal: 4),
                              decoration: selected
                                  ? const BoxDecoration(
                                      border: Border(
                                        left: BorderSide(
                                            color: kAccent, width: 2),
                                      ),
                                    )
                                  : null,
                              child: Row(
                                children: [
                                  Container(
                                    width: 6,
                                    height: 6,
                                    margin:
                                        const EdgeInsets.only(right: 10),
                                    decoration: BoxDecoration(
                                      color: selected ? kAccent : kTextMuted,
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          r.klasNaam,
                                          style: GoogleFonts.inter(
                                            color: selected ? kText1 : kText2,
                                            fontSize: 12,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                        Text(
                                          '${r.kampusNaam} · UID: ${r.nfcUid ?? "-"}',
                                          style: GoogleFonts.inter(
                                              color: kTextMuted,
                                              fontSize: 10),
                                        ),
                                      ],
                                    ),
                                  ),
                                  if (selected)
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: const Color(0x1F7B61FF),
                                        border: Border.all(
                                            color: kBorderEm, width: 1),
                                        borderRadius:
                                            BorderRadius.circular(999),
                                      ),
                                      child: Text(
                                        'Gekies',
                                        style: GoogleFonts.inter(
                                          color: const Color(0xFFA78BFA),
                                          fontSize: 8,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── NFC tab ──────────────────────────────────────────────────────────────────
class _NfcTab extends StatelessWidget {
  final int? gekoseLokasieId;
  final VoidCallback onSkryf;
  final VoidCallback onHerlaai;

  const _NfcTab({
    required this.gekoseLokasieId,
    required this.onSkryf,
    required this.onHerlaai,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(bottom: 20),
            child: Text(
              'NFC Skryf',
              style: GoogleFonts.inter(
                color: kText1,
                fontSize: 22,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          GlassCard(
            padding: const EdgeInsets.all(16),
            borderColor: const Color(0x737B61FF),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.nfc, color: kAccent, size: 22),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        gekoseLokasieId == null
                          ? 'Kies \'n klas in die Klasse-tab'
                          : 'Klas gekies — gaan terug na Klasse om UID te sien',
                        style: GoogleFonts.inter(
                          color: gekoseLokasieId == null ? kTextMuted : kText2,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: GradientActionButton(
                        label: 'Skryf NFC',
                        onTap: onSkryf,
                        height: 44,
                      ),
                    ),
                    const SizedBox(width: 12),
                    OutlineActionButton(
                      label: 'Herlaai',
                      onTap: onHerlaai,
                      width: 90,
                      height: 44,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color valueColor;
  final String badge;
  final Color badgeColor;

  const _StatCard({
    required this.label,
    required this.value,
    required this.valueColor,
    required this.badge,
    required this.badgeColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
      decoration: kGlassDecoration(radius: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: GoogleFonts.inter(
              color: kTextMuted,
              fontSize: 9,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: GoogleFonts.inter(
              color: valueColor,
              fontSize: 32,
              fontWeight: FontWeight.w800,
              height: 1,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            badge,
            style: GoogleFonts.inter(
              color: badgeColor,
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfielTab extends StatelessWidget {
  const _ProfielTab();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text('Profiel',
          style: GoogleFonts.inter(color: kTextMuted, fontSize: 14)),
    );
  }
}

// ─── Bottom nav ────────────────────────────────────────────────────────────────
class _AdminNavBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onTap;

  const _AdminNavBar({required this.selectedIndex, required this.onTap});

  @override
  Widget build(BuildContext context) {
    const items = [
      _NavItem(icon: Icons.home_rounded, label: 'Tuis'),
      _NavItem(icon: Icons.list_alt_rounded, label: 'Klasse'),
      _NavItem(icon: Icons.nfc_rounded, label: 'NFC'),
      _NavItem(icon: Icons.person_rounded, label: 'Profiel'),
    ];

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0D1120),
        border: const Border(top: BorderSide(color: Color(0x1AFFFFFF), width: 1)),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.4),
              blurRadius: 20,
              offset: const Offset(0, -4)),
        ],
      ),
      padding: EdgeInsets.only(
        top: 10,
        bottom: MediaQuery.of(context).padding.bottom + 10,
      ),
      child: Row(
        children: List.generate(items.length, (i) {
          final active = i == selectedIndex;
          return Expanded(
            child: GestureDetector(
              onTap: () => onTap(i),
              behavior: HitTestBehavior.opaque,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: active ? 28 : 0,
                    height: 2,
                    margin: const EdgeInsets.only(bottom: 6),
                    decoration: BoxDecoration(
                      color: active ? kAccent : Colors.transparent,
                      borderRadius: BorderRadius.circular(1),
                    ),
                  ),
                  Icon(items[i].icon,
                      size: 22, color: active ? kAccent : kTextMuted),
                  const SizedBox(height: 4),
                  Text(
                    items[i].label,
                    style: GoogleFonts.inter(
                      color: active ? kText1 : kTextMuted,
                      fontSize: 10,
                      fontWeight: active ? FontWeight.w600 : FontWeight.w400,
                    ),
                  ),
                ],
              ),
            ),
          );
        }),
      ),
    );
  }
}

class _NavItem {
  final IconData icon;
  final String label;
  const _NavItem({required this.icon, required this.label});
}
