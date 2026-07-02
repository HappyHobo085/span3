import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';
import 'package:nfc_manager/nfc_manager.dart';
import 'dart:convert';
import 'package:qr_flutter/qr_flutter.dart';
import 'profile_page.dart';

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
class _TuisTab extends StatefulWidget {
  const _TuisTab();

  @override
  State<_TuisTab> createState() => _TuisTabState();
}

class _TuisTabState extends State<_TuisTab> {
  bool _loading = true;
  Map<String, dynamic>? _dashboard;
  Map<String, dynamic>? _profile;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    try {
      final profile = MoonApi.myProfile ?? await MoonApi.getMyProfile();
      final dashboard = await MoonApi.fetchDashboard();

      if (!mounted) return;

      setState(() {
        _profile = profile;
        _dashboard = dashboard;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  String _formatTime(dynamic value) {
    if (value == null) return 'Geen scan';

    try {
      final dt = DateTime.parse(value.toString());
      final h = dt.hour.toString().padLeft(2, '0');
      final m = dt.minute.toString().padLeft(2, '0');
      return '$h:$m';
    } catch (_) {
      return value.toString();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Text(
          _error!,
          style: GoogleFonts.inter(color: Colors.red, fontSize: 13),
        ),
      );
    }

    final naam = _profile?['naam']?.toString() ?? 'Student';
    final kampusStatus = _dashboard?['kampus_status']?.toString() ?? 'ONBEKEND';

    final opKampus = kampusStatus == 'OP_KAMPUS';

    final laasteKampus = _dashboard?['laaste_kampus'];
    final laasteKlas = _dashboard?['laaste_klas'];

    return RefreshIndicator(
      onRefresh: _loadDashboard,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Row(
                children: [
                  const Icon(Icons.waving_hand_rounded, color: kAccent, size: 28),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Welkom, $naam',
                      style: GoogleFonts.inter(
                        color: kText1,
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 14),

            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: opKampus
                    ? Colors.green.withOpacity(0.16)
                    : Colors.red.withOpacity(0.14),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: opKampus ? Colors.green : Colors.red,
                  width: 1.5,
                ),
              ),
              child: Column(
                children: [
                  Icon(
                    opKampus ? Icons.check_circle : Icons.cancel,
                    color: opKampus ? Colors.green : Colors.red,
                    size: 46,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    opKampus ? 'OP KAMPUS' : 'NIE OP KAMPUS',
                    style: GoogleFonts.inter(
                      color: opKampus ? Colors.green : Colors.red,
                      fontSize: 20,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 14),

            _DashboardInfoCard(
              title: 'LAASTE KAMPUS SCAN',
              icon: Icons.location_on_outlined,
              mainText: laasteKampus == null
                  ? 'Geen kampus scan'
                  : laasteKampus['lokasie']?.toString() ?? 'Onbekend',
              subText: laasteKampus == null
                  ? 'Nog geen IN/UIT scan nie'
                  : '${laasteKampus['rigting']} · ${_formatTime(laasteKampus['tyd'])}',
            ),

            const SizedBox(height: 12),

            _DashboardInfoCard(
              title: 'LAASTE KLAS SCAN',
              icon: Icons.school_outlined,
              mainText: laasteKlas == null
                  ? 'Geen klas scan'
                  : laasteKlas['lokasie']?.toString() ?? 'Onbekend',
              subText: laasteKlas == null
                  ? 'Nog geen klas NFC scan nie'
                  : '${_formatTime(laasteKlas['tyd'])}',
            ),

            const SizedBox(height: 16),

            Row(
              children: [
                Expanded(
                  child: GradientActionButton(
                  label: 'Wys QR',
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const LeftEmptyPage(),
                      ),
                    );
                  },
                  height: 50,
                ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: GradientActionButton(
                  label: 'Scan Klas',
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const RightEmptyPage(
                        ),
                      ),
                    );
                  },
                  height: 50,
                ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _DashboardInfoCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final String mainText;
  final String subText;

  const _DashboardInfoCard({
    required this.title,
    required this.icon,
    required this.mainText,
    required this.subText,
  });

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Icon(icon, color: kAccent, size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.inter(
                    color: kTextMuted,
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.1,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  mainText,
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  subText,
                  style: GoogleFonts.inter(
                    color: kText2,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
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
    return const ProfilePage();
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
class LeftEmptyPage extends StatefulWidget {
  const LeftEmptyPage({super.key});

  @override
  State<LeftEmptyPage> createState() => _LeftEmptyPageState();
}

class _LeftEmptyPageState extends State<LeftEmptyPage> {
  bool _loading = true;
  String? _studentNommer;
  String _status = 'Laai student profiel...';

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      if (MoonApi.myProfile == null) {
        await MoonApi.getMyProfile();
      }

      setState(() {
        _studentNommer = MoonApi.myStudentNommer;
        _loading = false;
        _status = 'Hou jou foon teen die MT90';
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _status = 'Kon nie studentenommer laai nie';
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Fout: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final nommer = _studentNommer ?? 'Onbekend';

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
                  padding: const EdgeInsets.all(20),
                  child: Center(
                    child: _loading
                        ? const CircularProgressIndicator()
                        : Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(
                                Icons.nfc,
                                color: kAccent,
                                size: 72,
                              ),
                              const SizedBox(height: 20),
                              Text(
                                'Studentenommer',
                                style: GoogleFonts.inter(
                                  color: kTextMuted,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                nommer,
                                style: GoogleFonts.inter(
                                  color: kText1,
                                  fontSize: 42,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 2,
                                ),
                              ),
                              const SizedBox(height: 20),
                              Text(
                                _status,
                                textAlign: TextAlign.center,
                                style: GoogleFonts.inter(
                                  color: kText2,
                                  fontSize: 14,
                                ),
                              ),
                              const SizedBox(height: 24),
                              GlassCard(
                                padding: const EdgeInsets.all(14),
                                child: Column(
                                  children: [
                                    Text(
                                      'QR Backup',
                                      style: GoogleFonts.inter(
                                        color: kTextMuted,
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    const SizedBox(height: 12),
                                    Container(
                                      color: Colors.white,
                                      padding: const EdgeInsets.all(10),
                                      child: QrImageView(
                                        data: nommer,
                                        version: QrVersions.auto,
                                        size: 170,
                                      ),
                                    ),
                                  ],
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
