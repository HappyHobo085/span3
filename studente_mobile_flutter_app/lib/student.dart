import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';
import 'package:nfc_manager/nfc_manager.dart';
import 'dart:convert';

// ─── Student Home — dashboard with bottom nav ────────────────────────────────
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedIndex = 0;

  void _onNavTap(int index) {
    if (index == 1) {
      // Skandeer — navigate to scanning flow
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const ScanSelectionPage()),
      );
      return;
    }
    setState(() => _selectedIndex = index);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            // ── NFC status bar ──────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [NfcStatusBadge()],
              ),
            ),
            // ── Page content ────────────────────────────────────────────
            Expanded(
              child: _selectedIndex == 0
                  ? const _TuisTab()
                  : _selectedIndex == 2
                      ? const _RoosterTab()
                      : const _ProfielTab(),
            ),
          ],
        ),
      ),
      // ── Bottom navigation bar ───────────────────────────────────────────
      bottomNavigationBar: _StudentNavBar(
        selectedIndex: _selectedIndex,
        onTap: _onNavTap,
      ),
    );
  }
}

// ─── Tuis (Home) tab ─────────────────────────────────────────────────────────
class _TuisTab extends StatelessWidget {
  const _TuisTab();

  @override
  Widget build(BuildContext context) {
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
                        'Student',
                        style: GoogleFonts.inter(
                          color: kTextMuted,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                // Notification icon
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: kSurface1,
                    border: Border.all(color: kBorder, width: 1.5),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.notifications_outlined,
                    color: kTextMuted,
                    size: 18,
                  ),
                ),
              ],
            ),
          ),

          // ── Stat cards row ────────────────────────────────────────────
          Row(
            children: [
              Expanded(child: _StatCard(
                label: 'KAMPUSSE',
                value: '3',
                valueColor: kText1,
                badge: '♦ Aktief',
                badgeColor: kSuccess,
              )),
              const SizedBox(width: 12),
              Expanded(child: _StatCard(
                label: 'AANWESIG',
                value: '94%',
                valueColor: kAccent2,
                badge: '♦ Hierdie week',
                badgeColor: kAccent2,
              )),
            ],
          ),

          const SizedBox(height: 12),

          // ── Volgende Klas card ────────────────────────────────────────
          _NextClassCard(),
        ],
      ),
    );
  }
}

// ─── Stat card ───────────────────────────────────────────────────────────────
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

// ─── Next class card ─────────────────────────────────────────────────────────
class _NextClassCard extends StatelessWidget {
  const _NextClassCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
      decoration: kGlassDecoration(radius: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'VOLGENDE KLAS',
            style: GoogleFonts.inter(
              color: kTextMuted,
              fontSize: 9,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            'Wiskunde 301',
            style: GoogleFonts.inter(
              color: kText1,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Lokaal B204 · 10:30',
            style: GoogleFonts.inter(
              color: kText2,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Placeholder tabs ─────────────────────────────────────────────────────────
class _RoosterTab extends StatelessWidget {
  const _RoosterTab();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        'Rooster',
        style: GoogleFonts.inter(color: kTextMuted, fontSize: 14),
      ),
    );
  }
}

class _ProfielTab extends StatelessWidget {
  const _ProfielTab();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        'Profiel',
        style: GoogleFonts.inter(color: kTextMuted, fontSize: 14),
      ),
    );
  }
}

// ─── Bottom navigation bar ───────────────────────────────────────────────────
class _StudentNavBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onTap;

  const _StudentNavBar({
    required this.selectedIndex,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    const items = [
      _NavItem(icon: Icons.home_rounded, label: 'Tuis'),
      _NavItem(icon: Icons.nfc_rounded, label: 'Skandeer'),
      _NavItem(icon: Icons.calendar_today_rounded, label: 'Rooster'),
      _NavItem(icon: Icons.person_rounded, label: 'Profiel'),
    ];

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0D1120),
        border: const Border(
          top: BorderSide(color: Color(0x1AFFFFFF), width: 1),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.4),
            blurRadius: 20,
            offset: const Offset(0, -4),
          ),
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
                  // Active indicator dot
                  Container(
                    width: active ? 28 : 0,
                    height: 2,
                    margin: const EdgeInsets.only(bottom: 6),
                    decoration: BoxDecoration(
                      color: active ? kAccent : Colors.transparent,
                      borderRadius: BorderRadius.circular(1),
                    ),
                  ),
                  Icon(
                    items[i].icon,
                    size: 22,
                    color: active ? kAccent : kTextMuted,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    items[i].label,
                    style: GoogleFonts.inter(
                      color: active ? kText1 : kTextMuted,
                      fontSize: 10,
                      fontWeight:
                          active ? FontWeight.w600 : FontWeight.w400,
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

// ─── Scan selection page ──────────────────────────────────────────────────────
class ScanSelectionPage extends StatelessWidget {
  const ScanSelectionPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Skandeer',
              subtitle: 'Student',
              showBack: true,
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: GlassTapPanel(
                        label: 'Kampus Skandering',
                        subtitle: 'Tap om te skandeer',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const LeftEmptyPage()),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: GlassTapPanel(
                        label: 'Klas Skandering',
                        subtitle: 'Tap om te skandeer',
                        borderColor: const Color(0x3300C2FF),
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const RightEmptyPage()),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Kampus scanning placeholder ─────────────────────────────────────────────
class LeftEmptyPage extends StatelessWidget {
  const LeftEmptyPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Kampus Skandering',
              subtitle: 'Student',
              showBack: true,
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: GlassCard(
                  child: Center(
                    child: Text(
                      'Skandeer area',
                      style: GoogleFonts.inter(color: kTextMuted, fontSize: 13),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Class scanning placeholder ───────────────────────────────────────────────
class RightEmptyPage extends StatefulWidget {
  const RightEmptyPage({super.key});

  @override
  State<RightEmptyPage> createState() => _RightEmptyPageState();
}

class _RightEmptyPageState extends State<RightEmptyPage> {
  bool _busy = false;
  String _status = 'Tap om klas te skandeer';

  Future<void> _scanKlas() async {
    setState(() {
      _busy = true;
      _status = 'Hou NFC tag teen toestel...';
    });

    try {
      await NfcManager.instance.startSession(
        onDiscovered: (tag) async {
          try {
            String uid = '';

            final ndef = Ndef.from(tag);

            if (ndef != null) {
              final message = await ndef.read();

              for (final record in message.records) {
                if (record.typeNameFormat == NdefTypeNameFormat.nfcWellknown &&
                    String.fromCharCodes(record.type) == 'T') {
                  final payload = record.payload;

                  if (payload.isNotEmpty) {
                    final languageCodeLength = payload.first & 0x3F;
                    uid = utf8.decode(
                      payload.sublist(1 + languageCodeLength),
                    ).trim().toUpperCase();
                  }
                }
              }
            }

            debugPrint('NDEF UID GELEES = $uid');

            if (uid.isEmpty) {
              await NfcManager.instance.stopSession(
                errorMessage: 'Geen UID gevind nie',
              );
              return;
            }
            debugPrint('UID WAT NA BACKEND GESTUUR WORD = [$uid]');
            final result = await MoonApi.studentScanKlas(
              nfcUid: uid,
              rigting: 'IN',
            );

            await NfcManager.instance.stopSession();

            if (!mounted) return;

            setState(() {
              _busy = false;
              _status =
                  'Welkom by ${result["LOK_Naam"]}';
            });

            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                backgroundColor: Colors.green,
                content: Text(
                  '${result["LOK_Naam"]} aangeteken',
                  style: const TextStyle(color: Colors.white),
                ),
              ),
            );
          } catch (e) {
            await NfcManager.instance.stopSession();

            if (!mounted) return;

            setState(() {
              _busy = false;
              _status = 'Fout';
            });

            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                backgroundColor: Colors.red,
                content: Text(
                  '$e',
                  style: const TextStyle(color: Colors.white),
                ),
              ),
            );
          }
        },
      );
    } catch (e) {
      setState(() {
        _busy = false;
        _status = 'Fout';
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(
            '$e',
            style: const TextStyle(color: Colors.white),
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Klas Skandering',
              subtitle: 'Student',
              showBack: true,
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: GlassCard(
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.nfc,
                          color: kAccent,
                          size: 64,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _status,
                          style: GoogleFonts.inter(
                            color: kText1,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 20),
                        ElevatedButton(
                          onPressed: _busy ? null : _scanKlas,
                          child: Text(
                            _busy
                                ? 'Besig...'
                                : 'Scan Klas',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
