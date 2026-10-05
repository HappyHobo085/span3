import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';
import 'package:nfc_manager/nfc_manager.dart';
import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'package:qr_flutter/qr_flutter.dart';
import 'profile_page.dart';
import 'saamry_pickup_map.dart';


ThemeData _moonPickerTheme(BuildContext context) {
  final base = Theme.of(context);

  return base.copyWith(
    brightness: Brightness.dark,
    colorScheme: base.colorScheme.copyWith(
      brightness: Brightness.dark,
      primary: kAccent,
      onPrimary: Colors.black,
      surface: const Color(0xFF0F172A),
      onSurface: Colors.white,
    ),
    datePickerTheme: const DatePickerThemeData(
      backgroundColor: Color(0xFF0F172A),
      surfaceTintColor: Colors.transparent,
      headerBackgroundColor: Color(0xFF111827),
      headerForegroundColor: Colors.white,
      dividerColor: Color(0xFF334155),
    ),
    timePickerTheme: const TimePickerThemeData(
      backgroundColor: Color(0xFF0F172A),
      hourMinuteColor: Color(0xFF1E293B),
      hourMinuteTextColor: Colors.white,
      dialBackgroundColor: Color(0xFF111827),
      dialHandColor: kAccent,
      dialTextColor: Colors.white,
      entryModeIconColor: kAccent,
      dayPeriodColor: Color(0xFF1E293B),
      dayPeriodTextColor: Colors.white,
    ),
  );
}


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
                  ? _TuisTab(onSaamry: () => setState(() => _selectedIndex = 2), onVisitors: () => setState(() => _selectedIndex = 3))
                  : _selectedIndex == 2
                      ? const SaamryTab()
                      : _selectedIndex == 3
                          ? const _VisitorsTab()
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
  final VoidCallback onSaamry;
  final VoidCallback onVisitors;

  const _TuisTab({required this.onSaamry, required this.onVisitors});

  @override
  State<_TuisTab> createState() => _TuisTabState();
}

class _TuisTabState extends State<_TuisTab> {
  bool _loading = true;
  Map<String, dynamic>? _dashboard;
  Map<String, dynamic>? _profile;
  Map<String, dynamic>? _koshuisStatus;
  String? _error;
  String? _koshuisError;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  Future<void> _loadDashboard() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
        _koshuisError = null;
      });
    }

    try {
      final profile = MoonApi.myProfile ?? await MoonApi.getMyProfile();
      final dashboard = await MoonApi.fetchDashboard();

      Map<String, dynamic> koshuisStatus = <String, dynamic>{
        'is_koshuis_student': false,
      };
      String? koshuisError;

      try {
        koshuisStatus = await MoonApi.fetchMyKoshuisStatus();
      } catch (e) {
        koshuisError = e.toString().replaceFirst('Exception: ', '');
      }

      if (!mounted) return;

      setState(() {
        _profile = profile;
        _dashboard = dashboard;
        _koshuisStatus = koshuisStatus;
        _koshuisError = koshuisError;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  DateTime? _saDateTime(dynamic value) {
    if (value == null) return null;
    try {
      return DateTime.parse(value.toString()).add(const Duration(hours: 2));
    } catch (_) {
      return null;
    }
  }

  String _formatTime(dynamic value) {
    final dt = _saDateTime(value);
    if (dt == null) return 'Geen scan';
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }

  String _formatDateTime(dynamic value) {
    final dt = _saDateTime(value);
    if (dt == null) return 'Geen scan';
    const months = <String>[
      'Jan', 'Feb', 'Mrt', 'Apr', 'Mei', 'Jun',
      'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des',
    ];
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '${dt.day} ${months[dt.month - 1]} · $h:$m';
  }

  void _openStatusDetail({
    required String title,
    required String locationName,
    required String statusText,
    required bool? isIn,
    required Map<String, dynamic>? lastScan,
    required IconData icon,
  }) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => _StudentStatusDetailPage(
          title: title,
          locationName: locationName,
          statusText: statusText,
          isIn: isIn,
          lastScan: lastScan,
          icon: icon,
          formatDateTime: _formatDateTime,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            _error!,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(color: Colors.red, fontSize: 13),
          ),
        ),
      );
    }

    final naam = _profile?['naam']?.toString() ?? 'Student';
    final kampusStatus = _dashboard?['kampus_status']?.toString() ?? 'ONBEKEND';
    final Map<String, dynamic>? laasteKampus = _dashboard?['laaste_kampus'] is Map
        ? Map<String, dynamic>.from(_dashboard!['laaste_kampus'] as Map)
        : null;
    final Map<String, dynamic>? laasteKlas = _dashboard?['laaste_klas'] is Map
        ? Map<String, dynamic>.from(_dashboard!['laaste_klas'] as Map)
        : null;

    final bool? opKampus = kampusStatus == 'OP_KAMPUS'
        ? true
        : kampusStatus == 'NIE_OP_KAMPUS'
            ? false
            : null;
    final kampusStatusText = opKampus == true
        ? 'OP KAMPUS'
        : opKampus == false
            ? 'NIE OP KAMPUS'
            : 'NOG NIE GESCAN';
    final kampusNaam = laasteKampus?['lokasie']?.toString() ?? 'Kampus';

    final isKoshuisStudent = _koshuisStatus?['is_koshuis_student'] == true;
    final koshuisNaam = _koshuisStatus?['koshuis_naam']?.toString() ?? 'Koshuis';
    final koshuisRawStatus = _koshuisStatus?['status']?.toString() ?? 'ONBEKEND';
    final Map<String, dynamic>? laasteKoshuis = _koshuisStatus?['laaste_scan'] is Map
        ? Map<String, dynamic>.from(_koshuisStatus!['laaste_scan'] as Map)
        : null;
    final bool? inKoshuis = koshuisRawStatus == 'IN'
        ? true
        : koshuisRawStatus == 'UIT'
            ? false
            : null;
    final koshuisStatusText = inKoshuis == true
        ? 'IN KOSHUIS'
        : inKoshuis == false
            ? 'UIT KOSHUIS'
            : 'NOG NIE GESCAN';

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

            const SizedBox(height: 18),
            Text(
              'MY STATUS',
              style: GoogleFonts.inter(
                color: kTextMuted,
                fontSize: 9,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 10),

            LayoutBuilder(
              builder: (context, constraints) {
                final twoColumns = isKoshuisStudent && constraints.maxWidth >= 430;
                final width = twoColumns
                    ? (constraints.maxWidth - 12) / 2
                    : constraints.maxWidth;

                final cards = <Widget>[
                  SizedBox(
                    width: width,
                    child: _StudentPresenceCard(
                      title: 'KAMPUS',
                      locationName: kampusNaam,
                      statusText: kampusStatusText,
                      isIn: opKampus,
                      icon: Icons.location_on_rounded,
                      lastScanText: laasteKampus == null
                          ? 'Nog geen kampus IN/UIT scan nie'
                          : '${laasteKampus['rigting']} · ${_formatDateTime(laasteKampus['tyd'])}',
                      onTap: () => _openStatusDetail(
                        title: 'Kampusstatus',
                        locationName: kampusNaam,
                        statusText: kampusStatusText,
                        isIn: opKampus,
                        lastScan: laasteKampus,
                        icon: Icons.location_on_rounded,
                      ),
                    ),
                  ),
                ];

                if (isKoshuisStudent) {
                  cards.add(
                    SizedBox(
                      width: width,
                      child: _StudentPresenceCard(
                        title: 'KOSHUIS',
                        locationName: koshuisNaam,
                        statusText: koshuisStatusText,
                        isIn: inKoshuis,
                        icon: Icons.bed_rounded,
                        lastScanText: laasteKoshuis == null
                            ? 'Nog geen koshuis IN/UIT scan nie'
                            : '${laasteKoshuis['rigting']} · ${_formatDateTime(laasteKoshuis['tyd'])}',
                        onTap: () => _openStatusDetail(
                          title: 'Koshuisstatus',
                          locationName: koshuisNaam,
                          statusText: koshuisStatusText,
                          isIn: inKoshuis,
                          lastScan: laasteKoshuis,
                          icon: Icons.bed_rounded,
                        ),
                      ),
                    ),
                  );
                }

                return Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: cards,
                );
              },
            ),

            if (_koshuisError != null) ...[
              const SizedBox(height: 10),
              GlassCard(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Koshuisstatus kon nie laai nie: $_koshuisError',
                        style: GoogleFonts.inter(color: kText2, fontSize: 11),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 14),
            _DashboardInfoCard(
              title: 'LAASTE KLAS SCAN',
              icon: Icons.school_outlined,
              mainText: laasteKlas == null
                  ? 'Geen klas scan'
                  : laasteKlas['lokasie']?.toString() ?? 'Onbekend',
              subText: laasteKlas == null
                  ? 'Nog geen klas NFC scan nie'
                  : '${laasteKlas['rigting'] ?? ''} · ${_formatTime(laasteKlas['tyd'])}',
            ),

            const SizedBox(height: 18),
            Text(
              'VINNIGE AKSIES',
              style: GoogleFonts.inter(
                color: kTextMuted,
                fontSize: 9,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.1,
              ),
            ),
            const SizedBox(height: 10),
            LayoutBuilder(
              builder: (context, constraints) {
                final available = constraints.maxWidth;
                final columns = available >= 820 ? 3 : available >= 430 ? 2 : 1;
                final tileWidth = (available - ((columns - 1) * 12)) / columns;
                return Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    SizedBox(
                      width: tileWidth,
                      child: _StudentQuickAction(
                        icon: Icons.qr_code_2_rounded,
                        label: 'Wys QR',
                        subtitle: 'Kampustoegang',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const LeftEmptyPage()),
                        ),
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _StudentQuickAction(
                        icon: Icons.nfc_rounded,
                        label: 'Skandeer Klas',
                        subtitle: 'NFC klasinskandering',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const RightEmptyPage()),
                        ),
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _StudentQuickAction(
                        icon: Icons.event_rounded,
                        label: 'Events',
                        subtitle: 'Komende events & RSVP',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const _StudentEventsPage()),
                        ),
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _StudentQuickAction(
                        icon: Icons.directions_car_rounded,
                        label: 'Saamry',
                        subtitle: 'Bestuur jou groep',
                        onTap: widget.onSaamry,
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _StudentQuickAction(
                        icon: Icons.person_add_alt_1_rounded,
                        label: 'Besoekers',
                        subtitle: 'Skep uitnodiging',
                        onTap: widget.onVisitors,
                      ),
                    ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _StudentPresenceCard extends StatelessWidget {
  final String title;
  final String locationName;
  final String statusText;
  final bool? isIn;
  final IconData icon;
  final String lastScanText;
  final VoidCallback onTap;

  const _StudentPresenceCard({
    required this.title,
    required this.locationName,
    required this.statusText,
    required this.isIn,
    required this.icon,
    required this.lastScanText,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final statusColor = isIn == true
        ? Colors.green
        : isIn == false
            ? Colors.red
            : Colors.orange;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: statusColor.withOpacity(0.10),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: statusColor.withOpacity(0.65), width: 1.2),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, color: statusColor, size: 24),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      title,
                      style: GoogleFonts.inter(
                        color: kTextMuted,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.0,
                      ),
                    ),
                  ),
                  const Icon(Icons.chevron_right_rounded, color: kTextMuted, size: 20),
                ],
              ),
              const SizedBox(height: 14),
              Text(
                statusText,
                style: GoogleFonts.inter(
                  color: statusColor,
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                locationName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: GoogleFonts.inter(
                  color: kText1,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                lastScanText,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: GoogleFonts.inter(color: kText2, fontSize: 10),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StudentStatusDetailPage extends StatelessWidget {
  final String title;
  final String locationName;
  final String statusText;
  final bool? isIn;
  final Map<String, dynamic>? lastScan;
  final IconData icon;
  final String Function(dynamic) formatDateTime;

  const _StudentStatusDetailPage({
    required this.title,
    required this.locationName,
    required this.statusText,
    required this.isIn,
    required this.lastScan,
    required this.icon,
    required this.formatDateTime,
  });

  @override
  Widget build(BuildContext context) {
    final statusColor = isIn == true
        ? Colors.green
        : isIn == false
            ? Colors.red
            : Colors.orange;

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(title: title, subtitle: locationName, showBack: true),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(22),
                      decoration: BoxDecoration(
                        color: statusColor.withOpacity(0.10),
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(color: statusColor.withOpacity(0.7)),
                      ),
                      child: Column(
                        children: [
                          Icon(icon, color: statusColor, size: 44),
                          const SizedBox(height: 10),
                          Text(
                            statusText,
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: statusColor,
                              fontSize: 22,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            locationName,
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    GlassCard(
                      padding: const EdgeInsets.all(16),
                      child: lastScan == null
                          ? Row(
                              children: [
                                const Icon(Icons.history_rounded, color: kTextMuted),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    'Nog geen IN/UIT skandering beskikbaar nie.',
                                    style: GoogleFonts.inter(color: kText2, fontSize: 12),
                                  ),
                                ),
                              ],
                            )
                          : Column(
                              children: [
                                _StudentStatusDetailRow(
                                  label: 'Laaste rigting',
                                  value: lastScan!['rigting']?.toString() ?? '—',
                                ),
                                _StudentStatusDetailRow(
                                  label: 'Tyd',
                                  value: formatDateTime(lastScan!['tyd']),
                                ),
                                _StudentStatusDetailRow(
                                  label: 'Metode',
                                  value: lastScan!['metode']?.toString() ?? '—',
                                ),
                                _StudentStatusDetailRow(
                                  label: 'Lokasie',
                                  value: lastScan!['lokasie']?.toString() ?? locationName,
                                  isLast: true,
                                ),
                              ],
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

class _StudentStatusDetailRow extends StatelessWidget {
  final String label;
  final String value;
  final bool isLast;

  const _StudentStatusDetailRow({
    required this.label,
    required this.value,
    this.isLast = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 11),
      decoration: BoxDecoration(
        border: isLast
            ? null
            : const Border(bottom: BorderSide(color: Color(0x1AFFFFFF))),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: GoogleFonts.inter(color: kTextMuted, fontSize: 11),
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: GoogleFonts.inter(
                color: kText1,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}


class _StudentQuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final String subtitle;
  final VoidCallback onTap;

  const _StudentQuickAction({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          padding: const EdgeInsets.all(16),
          decoration: kGlassDecoration(radius: 16),
          child: Row(
            children: [
              Icon(icon, color: kAccent, size: 28),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(color: kText1, fontSize: 14, fontWeight: FontWeight.w800)),
                    const SizedBox(height: 3),
                    Text(subtitle, maxLines: 2, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(color: kTextMuted, fontSize: 10)),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: kTextMuted, size: 20),
            ],
          ),
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
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  subText,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
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

// ─── Saamry tab — permanente groepe, eenmalige events en chat ───────────────

class SaamryTab extends StatefulWidget {
  const SaamryTab({super.key});

  @override
  State<SaamryTab> createState() => _SaamryTabState();
}

class _SaamryTabState extends State<SaamryTab> {
  bool _loading = true;
  bool _busy = false;
  String? _error;
  SaamryStatusDto? _status;
  Timer? _statusTimer;
  int? _selectedGroupId;
  bool _showPeople = false;

  @override
  void initState() {
    super.initState();
    _load();
    _statusTimer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _refreshQuietly(),
    );
  }

  @override
  void dispose() {
    _statusTimer?.cancel();
    super.dispose();
  }

  String _cleanError(Object error) =>
      error.toString().replaceFirst('Exception: ', '');

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final status = await MoonApi.fetchSaamryStatus();
      if (!mounted) return;
      setState(() {
        _status = status;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _cleanError(e);
        _loading = false;
      });
    }
  }

  Future<void> _refreshQuietly() async {
    if (!mounted || _busy) return;
    try {
      final status = await MoonApi.fetchSaamryStatus();
      if (!mounted) return;
      setState(() {
        _status = status;
        _error = null;
      });
    } catch (_) {
      // Hou die laaste geldige status; pull-to-refresh wys enige fout eksplisiet.
    }
  }

  void _message(String text, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: error ? Colors.red : null,
        content: Text(text),
      ),
    );
  }

  Future<void> _runAction(
    Future<void> Function() action,
    String success,
  ) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await action();
      if (!mounted) return;
      _message(success);
      await _load();
    } catch (e) {
      if (!mounted) return;
      _message(_cleanError(e), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<bool> _confirm({
    required String title,
    required String message,
    String confirmLabel = 'Bevestig',
  }) async {
    return await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            backgroundColor: const Color(0xFF111827),
            title: Text(title, style: const TextStyle(color: Colors.white)),
            content: Text(message, style: const TextStyle(color: Colors.white70)),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Kanselleer'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(confirmLabel),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _openCreateGroup() async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const CreateSaamryGroupPage()),
    );
    if (changed == true) await _load();
  }

  Future<void> _openAddFriend() async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const AddSaamryFriendPage()),
    );
    if (changed == true) await _load();
  }

  Future<void> _openCreateEvent({SaamryGroupDto? initialGroup}) async {
    final allGroups = _status?.groups ?? const <SaamryGroupDto>[];
    final ownedActive = allGroups
        .where((g) => g.isBestuurder && g.aktieweEvent != null)
        .toList();
    if (ownedActive.isNotEmpty) {
      _message(
        'Jy het reeds ’n aktiewe Saamry-event in ${ownedActive.first.naam}. Voltooi of kanselleer dit eers.',
      );
      return;
    }

    final driverGroups = allGroups
        .where((g) => g.isBestuurder && g.aktieweEvent == null)
        .where((g) => g.lede.any(
              (m) => !m.isBestuurder && m.status == 'AANVAAR',
            ))
        .toList();

    if (driverGroups.isEmpty) {
      _message(
        'Jy het geen Driver/Admin-groep wat gereed is vir ’n nuwe Saamry-event nie.',
      );
      return;
    }

    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => CreateSaamryEventPage(
          groups: driverGroups,
          initialGroupId: initialGroup?.groepId,
        ),
      ),
    );
    if (changed == true) await _load();
  }

  Future<void> _openInvite(SaamryGroupDto group) async {
    final existing = group.lede.map((e) => e.gebruiker.gebruikerId).toSet();
    final available = (_status?.friends ?? const <SaamryFriendItemDto>[])
        .where((friend) => !existing.contains(friend.gebruiker.gebruikerId))
        .toList();
    if (available.isEmpty) {
      _message('Geen beskikbare vriende om te nooi nie');
      return;
    }
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => InviteSaamryFriendPage(
          groepId: group.groepId,
          friends: available,
        ),
      ),
    );
    if (changed == true) await _load();
  }

  Future<void> _transferDriver(SaamryGroupDto group) async {
    final candidates = group.lede
        .where((m) => m.status == 'AANVAAR' && !m.isBestuurder)
        .toList();
    if (candidates.isEmpty) {
      _message('Daar is geen ander aanvaarde lid om Driver/Admin te maak nie');
      return;
    }

    final selected = await showDialog<SaamryGroupMemberDto>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF111827),
        title: const Text(
          'Gee Driver/Admin oor',
          style: TextStyle(color: Colors.white),
        ),
        content: SizedBox(
          width: 420,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: candidates
                .map(
                  (member) => ListTile(
                    leading: const Icon(
                      Icons.drive_eta_rounded,
                      color: kAccent,
                    ),
                    title: Text(
                      member.gebruiker.volleNaam,
                      style: const TextStyle(color: Colors.white),
                    ),
                    subtitle: Text(
                      '${member.gebruiker.rol} · ${member.gebruiker.nommer}',
                      style: const TextStyle(color: Colors.white60),
                    ),
                    onTap: () => Navigator.pop(context, member),
                  ),
                )
                .toList(),
          ),
        ),
      ),
    );
    if (selected == null) return;

    final confirm = await _confirm(
      title: 'Bevestig Driver/Admin',
      message:
          '${selected.gebruiker.volleNaam} word die nuwe Driver én Admin van ${group.naam}. Jy sal daarna ’n gewone lid wees.',
      confirmLabel: 'Gee Oor',
    );
    if (!confirm) return;

    await _runAction(
      () => MoonApi.transferSaamryDriver(
        groepId: group.groepId,
        nuweBestuurderId: selected.gebruiker.gebruikerId,
      ),
      'Driver/Admin is oorgedra',
    );
  }

  Future<void> _openFriendChat(SaamryFriendItemDto friend) async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (_) => SaamryChatPage(friend: friend.gebruiker),
      ),
    );
    await _load();
  }

  Future<void> _openGroupChat(SaamryGroupDto group) async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (_) => SaamryChatPage(group: group),
      ),
    );
    await _load();
  }

  Future<void> _openPickupMap(SaamryGroupDto group) async {
    final event = group.aktieweEvent;
    if (event == null || !event.isDeelnemer) {
      _message('Jy is nie deel van hierdie aktiewe Saamry-event nie');
      return;
    }
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (_) => SaamryPickupMapPage(group: group, event: event),
      ),
    );
    await _load();
  }

  Widget _sectionTitle(String text) => Text(
        text,
        style: GoogleFonts.inter(
          color: kTextMuted,
          fontSize: 9,
          fontWeight: FontWeight.w800,
          letterSpacing: 1.1,
        ),
      );

  Widget _avatar(SaamryUserDto user, {double size = 42}) {
    final raw = user.fotoUrl?.trim() ?? '';
    final imageUrl = raw.isEmpty
        ? null
        : (raw.startsWith('http') ? raw : '${MoonApi.baseUrl}$raw');
    return CircleAvatar(
      radius: size / 2,
      backgroundColor: Colors.white10,
      backgroundImage: imageUrl == null ? null : NetworkImage(imageUrl),
      child: imageUrl == null
          ? Text(
              user.naam.isEmpty ? '?' : user.naam[0].toUpperCase(),
              style: GoogleFonts.inter(
                color: kAccent,
                fontWeight: FontWeight.w800,
              ),
            )
          : null,
    );
  }

  Widget _badge(int count) {
    if (count <= 0) return const SizedBox.shrink();
    return Container(
      constraints: const BoxConstraints(minWidth: 22, minHeight: 22),
      padding: const EdgeInsets.symmetric(horizontal: 6),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: kAccent,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        '$count',
        style: const TextStyle(
          color: Colors.black,
          fontSize: 11,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }

  Widget _incomingFriendCard(SaamryFriendItemDto request) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: GlassCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Row(
              children: [
                _avatar(request.gebruiker),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    request.gebruiker.volleNaam,
                    style: GoogleFonts.inter(
                      color: kText1,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: GradientActionButton(
                    label: 'Aanvaar',
                    onTap: _busy
                        ? () {}
                        : () => _runAction(
                              () => MoonApi.acceptSaamryFriendRequest(
                                request.vriendskapId,
                              ),
                              '${request.gebruiker.volleNaam} is nou jou vriend',
                            ),
                    height: 44,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlineActionButton(
                    label: 'Weier',
                    onTap: _busy
                        ? () {}
                        : () => _runAction(
                              () => MoonApi.declineSaamryFriendRequest(
                                request.vriendskapId,
                              ),
                              'Versoek geweier',
                            ),
                    height: 44,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _groupInviteCard(SaamryGroupDto group) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: GlassCard(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              group.naam,
              style: GoogleFonts.inter(
                color: kText1,
                fontSize: 15,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Driver/Admin: ${group.bestuurder.volleNaam}',
              style: GoogleFonts.inter(color: kText2, fontSize: 12),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: GradientActionButton(
                    label: 'Sluit Aan',
                    onTap: _busy
                        ? () {}
                        : () => _runAction(
                              () async {
                                await MoonApi.acceptSaamryGroupInvite(group.groepId);
                              },
                              'Jy het by ${group.naam} aangesluit',
                            ),
                    height: 44,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlineActionButton(
                    label: 'Weier',
                    onTap: _busy
                        ? () {}
                        : () => _runAction(
                              () => MoonApi.declineSaamryGroupInvite(group.groepId),
                              'Groepuitnodiging geweier',
                            ),
                    height: 44,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _eventBanner(SaamryGroupDto group) {
    final event = group.aktieweEvent;
    if (event == null) {
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white12),
        ),
        child: Text(
          'Geen aktiewe Saamry-event nie. Almal scan individueel totdat ’n nuwe event geskep word.',
          style: GoogleFonts.inter(color: kText2, fontSize: 11.5),
        ),
      );
    }

    final passengers = event.lede.where((e) => !e.isBestuurder).length;
    SaamryEventMemberDto? me;
    for (final member in event.lede) {
      if (member.isMyne) {
        me = member;
        break;
      }
    }
    final myPinReady = me?.pickupGestel == true;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: kAccent.withOpacity(0.10),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: kAccent.withOpacity(0.45)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.directions_car_filled_rounded, color: kAccent),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'AKTIEWE SAAMRY-EVENT',
                      style: GoogleFonts.inter(
                        color: kAccent,
                        fontSize: 9,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '$passengers passasier${passengers == 1 ? '' : 's'} · ${event.pickupGereed}/${event.pickupTotaal} pins gereed',
                      style: GoogleFonts.inter(color: kText1, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (event.isDeelnemer) ...[
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: () => _openPickupMap(group),
              icon: Icon(
                myPinReady ? Icons.map_rounded : Icons.add_location_alt_rounded,
                size: 18,
              ),
              label: Text(
                event.isBestuurder
                    ? 'Pickup-kaart'
                    : (myPinReady ? 'Pickup-kaart / Verander Pin' : 'Stel My Optel-pin'),
              ),
            ),
          ],
        ],
      ),
    );
  }


  Widget _groupCard(SaamryGroupDto group) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.groups_2_rounded, color: kAccent, size: 28),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      group.naam,
                      style: GoogleFonts.inter(
                        color: kText1,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      'Driver/Admin: ${group.bestuurder.volleNaam}',
                      style: GoogleFonts.inter(color: kText2, fontSize: 11.5),
                    ),
                  ],
                ),
              ),
              if (group.isBestuurder)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                  decoration: BoxDecoration(
                    color: kAccent.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Text(
                    'DRIVER / ADMIN',
                    style: TextStyle(
                      color: kAccent,
                      fontSize: 8,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          _eventBanner(group),
          const SizedBox(height: 12),
          _sectionTitle('LEDE'),
          const SizedBox(height: 8),
          ...group.lede.map(
                (member) => Padding(
                  padding: const EdgeInsets.only(bottom: 7),
                  child: Row(
                    children: [
                      _avatar(member.gebruiker, size: 34),
                      const SizedBox(width: 9),
                      Expanded(
                        child: Text(
                          member.gebruiker.volleNaam,
                          style: GoogleFonts.inter(color: kText1, fontSize: 12),
                        ),
                      ),
                      if (member.isBestuurder)
                        const Text(
                          'DRIVER',
                          style: TextStyle(
                            color: kAccent,
                            fontSize: 9,
                            fontWeight: FontWeight.w900,
                          ),
                        )
                      else if (member.status == 'HANGEND')
                        const Text(
                          'HANGEND',
                          style: TextStyle(
                            color: Colors.orangeAccent,
                            fontSize: 9,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _openGroupChat(group),
                  icon: const Icon(Icons.chat_bubble_outline_rounded, size: 18),
                  label: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text('Groepchat'),
                      if (group.ongelees > 0) ...[
                        const SizedBox(width: 6),
                        _badge(group.ongelees),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
          if (group.isBestuurder) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: GradientActionButton(
                    label: group.aktieweEvent == null ? 'Nuwe Saamry' : 'Event Aktief',
                    onTap: group.aktieweEvent == null
                        ? () => _openCreateEvent(initialGroup: group)
                        : () {},
                    height: 44,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlineActionButton(
                    label: 'Nooi Vriend',
                    onTap: () => _openInvite(group),
                    height: 44,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlineActionButton(
                    label: 'Gee Driver Oor',
                    onTap: () => _transferDriver(group),
                    height: 44,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlineActionButton(
                    label: group.aktieweEvent != null ? 'Kanselleer Event' : 'Sluit Groep',
                    onTap: _busy
                        ? () {}
                        : () async {
                            if (group.aktieweEvent != null) {
                              final ok = await _confirm(
                                title: 'Kanselleer Saamry-event',
                                message: 'Die permanente groep bly bestaan; net hierdie aktiewe rit word gekanselleer.',
                                confirmLabel: 'Kanselleer Event',
                              );
                              if (!ok) return;
                              await _runAction(
                                () => MoonApi.cancelSaamryEvent(group.aktieweEvent!.eventId),
                                'Saamry-event gekanselleer',
                              );
                            } else {
                              final ok = await _confirm(
                                title: 'Sluit Permanente Groep',
                                message: 'Dit sluit die permanente groep. Die groepchat en nuwe events sal daarna nie beskikbaar wees nie.',
                                confirmLabel: 'Sluit Groep',
                              );
                              if (!ok) return;
                              await _runAction(
                                () => MoonApi.closeSaamryGroup(group.groepId),
                                'Permanente Saamrygroep gesluit',
                              );
                            }
                          },
                    height: 44,
                  ),
                ),
              ],
            ),
          ] else ...[
            const SizedBox(height: 10),
            OutlineActionButton(
              label: 'Verlaat Groep',
              onTap: _busy
                  ? () {}
                  : () async {
                      final ok = await _confirm(
                        title: 'Verlaat Groep',
                        message: 'Jy sal nie meer die groepchat of toekomstige Saamry-events van hierdie groep sien nie.',
                        confirmLabel: 'Verlaat',
                      );
                      if (!ok) return;
                      await _runAction(
                        () => MoonApi.leaveSaamryGroup(group.groepId),
                        'Jy het die groep verlaat',
                      );
                    },
              height: 44,
            ),
          ],
        ],
      ),
    );
  }

  Widget _friendsCard(SaamryStatusDto status) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: _sectionTitle('VRIENDE & PRIVAAT CHAT')),
              TextButton.icon(
                onPressed: _openAddFriend,
                icon: const Icon(Icons.person_add_alt_1_rounded, size: 17),
                label: const Text('Voeg By'),
              ),
            ],
          ),
          if (status.friends.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Nog geen vriende nie',
                style: GoogleFonts.inter(color: kText2, fontSize: 12),
              ),
            )
          else
            ...status.friends.map(
              (friend) => Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Row(
                  children: [
                    _avatar(friend.gebruiker),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            friend.gebruiker.volleNaam,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          Text(
                            '${friend.gebruiker.rol} · ${friend.gebruiker.nommer}',
                            style: GoogleFonts.inter(color: kTextMuted, fontSize: 10.5),
                          ),
                        ],
                      ),
                    ),
                    Stack(
                      clipBehavior: Clip.none,
                      children: [
                        IconButton(
                          tooltip: 'Boodskap',
                          onPressed: () => _openFriendChat(friend),
                          icon: const Icon(Icons.chat_rounded, color: kAccent),
                        ),
                        if (friend.ongelees > 0)
                          Positioned(right: 0, top: 0, child: _badge(friend.ongelees)),
                      ],
                    ),
                    IconButton(
                      tooltip: 'Verwyder vriend',
                      onPressed: _busy
                          ? null
                          : () async {
                              final ok = await _confirm(
                                title: 'Verwyder Vriend',
                                message: 'Verwyder ${friend.gebruiker.volleNaam} uit jou vriende?',
                                confirmLabel: 'Verwyder',
                              );
                              if (!ok) return;
                              await _runAction(
                                () => MoonApi.removeSaamryFriend(
                                  friend.gebruiker.gebruikerId,
                                ),
                                'Vriend verwyder',
                              );
                            },
                      icon: const Icon(
                        Icons.person_remove_outlined,
                        color: kTextMuted,
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

  Widget _groupSummaryCard(SaamryGroupDto group) {
    final memberCount = group.lede.where((m) => m.status == 'AANVAAR').length;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        onTap: () => setState(() {
          _selectedGroupId = group.groepId;
          _showPeople = false;
        }),
        borderRadius: BorderRadius.circular(16),
        child: GlassCard(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 15),
          child: Row(
            children: [
              const Icon(Icons.groups_2_rounded, color: kAccent, size: 28),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      group.naam,
                      style: GoogleFonts.inter(
                        color: kText1,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      '$memberCount lid${memberCount == 1 ? '' : 'e'}',
                      style: GoogleFonts.inter(color: kTextMuted, fontSize: 11.5),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: kTextMuted),
            ],
          ),
        ),
      ),
    );
  }

  int _noticeCount(SaamryStatusDto status) =>
      status.incomingRequests.length + status.groupInvites.length;

  Widget _buildGroupsHome(SaamryStatusDto status) {
    final noticeCount = _noticeCount(status);
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Saamry',
                      style: GoogleFonts.inter(
                        color: kText1,
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    Text(
                      'My permanente groepe',
                      style: GoogleFonts.inter(color: kTextMuted, fontSize: 11.5),
                    ),
                  ],
                ),
              ),
              Stack(
                clipBehavior: Clip.none,
                children: [
                  IconButton(
                    tooltip: 'Vriende & uitnodigings',
                    onPressed: () => setState(() {
                      _showPeople = true;
                      _selectedGroupId = null;
                    }),
                    icon: const Icon(Icons.people_alt_rounded, color: kAccent),
                  ),
                  if (noticeCount > 0)
                    Positioned(right: 1, top: 1, child: _badge(noticeCount)),
                ],
              ),
              IconButton(
                tooltip: 'Herlaai',
                onPressed: _load,
                icon: const Icon(Icons.refresh_rounded, color: kAccent),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (status.groups.isEmpty)
            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Text(
                'Jy behoort nog nie aan ’n permanente Saamrygroep nie.',
                style: GoogleFonts.inter(color: kText2, fontSize: 12.5),
              ),
            )
          else
            ...status.groups.map(_groupSummaryCard),
          const SizedBox(height: 8),
          GradientActionButton(
            label: 'Nuwe Groep',
            onTap: _openCreateGroup,
            height: 48,
          ),
        ],
      ),
    );
  }

  Widget _buildPeopleView(SaamryStatusDto status) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          Row(
            children: [
              IconButton(
                tooltip: 'Terug',
                onPressed: () => setState(() => _showPeople = false),
                icon: const Icon(Icons.arrow_back_rounded, color: kText1),
              ),
              Expanded(
                child: Text(
                  'Vriende & Uitnodigings',
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          if (status.incomingRequests.isNotEmpty) ...[
            const SizedBox(height: 14),
            _sectionTitle('VRIENDSKAPVERSOEKE'),
            const SizedBox(height: 8),
            ...status.incomingRequests.map(_incomingFriendCard),
          ],
          if (status.groupInvites.isNotEmpty) ...[
            const SizedBox(height: 14),
            _sectionTitle('GROEPUITNODIGINGS'),
            const SizedBox(height: 8),
            ...status.groupInvites.map(_groupInviteCard),
          ],
          const SizedBox(height: 14),
          _friendsCard(status),
          if (status.outgoingRequests.isNotEmpty) ...[
            const SizedBox(height: 14),
            GlassCard(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _sectionTitle('HANGENDE VRIENDVERSOEKE'),
                  const SizedBox(height: 8),
                  ...status.outgoingRequests.map(
                    (request) => Padding(
                      padding: const EdgeInsets.only(bottom: 7),
                      child: Row(
                        children: [
                          const Icon(Icons.schedule_rounded, color: Colors.orangeAccent, size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              request.gebruiker.volleNaam,
                              style: GoogleFonts.inter(color: kText1, fontSize: 12),
                            ),
                          ),
                          Text(
                            'Hangend',
                            style: GoogleFonts.inter(color: kTextMuted, fontSize: 10),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildGroupDetail(SaamryGroupDto group) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          Row(
            children: [
              IconButton(
                tooltip: 'Terug na groepe',
                onPressed: () => setState(() => _selectedGroupId = null),
                icon: const Icon(Icons.arrow_back_rounded, color: kText1),
              ),
              Expanded(
                child: Text(
                  group.naam,
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              IconButton(
                tooltip: 'Herlaai',
                onPressed: _load,
                icon: const Icon(Icons.refresh_rounded, color: kAccent),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _groupCard(group),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading && _status == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _status == null) {
      return RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(24),
          children: [
            const SizedBox(height: 80),
            const Icon(Icons.error_outline, color: Colors.red, size: 48),
            const SizedBox(height: 12),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.red),
            ),
          ],
        ),
      );
    }

    final status = _status!;
    if (_showPeople) return _buildPeopleView(status);
    final selectedId = _selectedGroupId;
    if (selectedId != null) {
      final matches = status.groups.where((g) => g.groepId == selectedId).toList();
      if (matches.isNotEmpty) return _buildGroupDetail(matches.first);
    }
    return _buildGroupsHome(status);
  }

}

class CreateSaamryGroupPage extends StatefulWidget {
  const CreateSaamryGroupPage({super.key});

  @override
  State<CreateSaamryGroupPage> createState() => _CreateSaamryGroupPageState();
}

class _CreateSaamryGroupPageState extends State<CreateSaamryGroupPage> {
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _seatsController = TextEditingController(text: '4');
  bool _busy = false;

  @override
  void dispose() {
    _nameController.dispose();
    _seatsController.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final name = _nameController.text.trim();
    final seats = int.tryParse(_seatsController.text.trim());
    if (name.isEmpty) {
      _error('Gee die permanente groep ’n naam');
      return;
    }
    if (seats == null || seats < 1 || seats > 8) {
      _error('Passasiersitplekke moet tussen 1 en 8 wees');
      return;
    }
    setState(() => _busy = true);
    try {
      await MoonApi.createSaamryGroup(naam: name, sitplekke: seats);
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      _error(e.toString().replaceFirst('Exception: ', ''));
      setState(() => _busy = false);
    }
  }

  void _error(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(backgroundColor: Colors.red, content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Nuwe Permanente Groep',
              subtitle: 'Die Driver is outomaties die Admin',
              showBack: true,
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: GlassCard(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'GROEPNAAM',
                        style: GoogleFonts.inter(
                          color: kTextMuted,
                          fontSize: 9,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      GlassInput(
                        controller: _nameController,
                        hintText: 'bv. Werk Saamry',
                        prefixIcon: const Icon(Icons.groups_rounded, color: kTextMuted),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        'PASSASIERSITPLEKKE',
                        style: GoogleFonts.inter(
                          color: kTextMuted,
                          fontSize: 9,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      GlassInput(
                        controller: _seatsController,
                        hintText: '1 tot 8',
                        keyboardType: TextInputType.number,
                        prefixIcon: const Icon(Icons.event_seat_rounded, color: kTextMuted),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Die groep bly bestaan nadat ’n rit klaar is. Vir elke werklike rit skep die Driver later ’n nuwe Saamry-event.',
                        style: GoogleFonts.inter(color: kText2, fontSize: 11.5),
                      ),
                      const SizedBox(height: 20),
                      GradientActionButton(
                        label: _busy ? 'Skep...' : 'Skep Permanente Groep',
                        onTap: _busy ? () {} : _create,
                        height: 50,
                      ),
                    ],
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

class CreateSaamryEventPage extends StatefulWidget {
  final List<SaamryGroupDto> groups;
  final int? initialGroupId;

  const CreateSaamryEventPage({
    super.key,
    required this.groups,
    this.initialGroupId,
  });

  @override
  State<CreateSaamryEventPage> createState() => _CreateSaamryEventPageState();
}

class _CreateSaamryEventPageState extends State<CreateSaamryEventPage> {
  late int _groupId;
  final Set<int> _selected = <int>{};
  bool _busy = false;
  SaamryPinSelection? _driverPin;

  @override
  void initState() {
    super.initState();
    _groupId = widget.groups.any((g) => g.groepId == widget.initialGroupId)
        ? widget.initialGroupId!
        : widget.groups.first.groepId;
    _selectDefaultPassengers();
  }

  SaamryGroupDto get _group =>
      widget.groups.firstWhere((g) => g.groepId == _groupId);

  List<SaamryGroupMemberDto> get _passengers => _group.lede
      .where((m) => !m.isBestuurder && m.status == 'AANVAAR')
      .toList();

  void _selectDefaultPassengers() {
    _selected
      ..clear()
      ..addAll(_passengers.map((m) => m.gebruiker.gebruikerId));
  }

  Future<void> _pickDriverPin() async {
    final selected = await Navigator.push<SaamryPinSelection>(
      context,
      MaterialPageRoute(
        builder: (_) => SaamryPinPickerPage(
          title: 'Driver Begin-pin',
          subtitle: _group.naam,
          initialLatitude: _driverPin?.latitude,
          initialLongitude: _driverPin?.longitude,
          initialBeskrywing: _driverPin?.beskrywing,
        ),
      ),
    );
    if (selected != null && mounted) {
      setState(() => _driverPin = selected);
    }
  }

  Future<void> _create() async {
    if (_selected.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Kies minstens een passasier')),
      );
      return;
    }
    if (_driverPin == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Stel eers die Driver se begin-pin')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      await MoonApi.createSaamryEvent(
        groepId: _groupId,
        gebruikerIds: _selected.toList(),
        driverLatitude: _driverPin!.latitude,
        driverLongitude: _driverPin!.longitude,
        driverPickupBeskrywing: _driverPin!.beskrywing,
      );
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
      setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Nuwe Saamry',
              subtitle: 'Kies permanente groep en passasiers',
              showBack: true,
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  GlassCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'PERMANENTE GROEP',
                          style: GoogleFonts.inter(
                            color: kTextMuted,
                            fontSize: 9,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 8),
                        DropdownButtonFormField<int>(
                          value: _groupId,
                          dropdownColor: const Color(0xFF111827),
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            filled: true,
                            fillColor: Colors.white.withOpacity(0.05),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                            ),
                          ),
                          items: widget.groups
                              .map(
                                (group) => DropdownMenuItem<int>(
                                  value: group.groepId,
                                  child: Text(group.naam),
                                ),
                              )
                              .toList(),
                          onChanged: _busy
                              ? null
                              : (value) {
                                  if (value == null) return;
                                  setState(() {
                                    _groupId = value;
                                    _selectDefaultPassengers();
                                  });
                                },
                        ),
                        const SizedBox(height: 14),
                        Text(
                          'Driver/Admin: ${_group.bestuurder.volleNaam}',
                          style: GoogleFonts.inter(
                            color: kAccent,
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 14),
                        OutlinedButton.icon(
                          onPressed: _busy ? null : _pickDriverPin,
                          icon: Icon(
                            _driverPin == null
                                ? Icons.add_location_alt_rounded
                                : Icons.location_on_rounded,
                          ),
                          label: Text(
                            _driverPin == null
                                ? 'Stel Driver se begin-pin'
                                : 'Begin-pin gestel · Verander',
                          ),
                        ),
                        if (_driverPin?.beskrywing?.trim().isNotEmpty == true) ...[
                          const SizedBox(height: 5),
                          Text(
                            _driverPin!.beskrywing!,
                            style: GoogleFonts.inter(color: kTextMuted, fontSize: 10.5),
                          ),
                        ],
                        const SizedBox(height: 16),
                        Text(
                          'WIE RY SAAM?',
                          style: GoogleFonts.inter(
                            color: kTextMuted,
                            fontSize: 9,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 8),
                        ..._passengers.map(
                          (member) => CheckboxListTile(
                            contentPadding: EdgeInsets.zero,
                            activeColor: kAccent,
                            checkColor: Colors.black,
                            title: Text(
                              member.gebruiker.volleNaam,
                              style: const TextStyle(color: Colors.white),
                            ),
                            subtitle: Text(
                              '${member.gebruiker.rol} · ${member.gebruiker.nommer}',
                              style: const TextStyle(color: Colors.white54),
                            ),
                            value: _selected.contains(member.gebruiker.gebruikerId),
                            onChanged: _busy
                                ? null
                                : (value) {
                                    setState(() {
                                      if (value == true) {
                                        _selected.add(member.gebruiker.gebruikerId);
                                      } else {
                                        _selected.remove(member.gebruiker.gebruikerId);
                                      }
                                    });
                                  },
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Geen tyd word gebruik om die event te voltooi nie. Sodra die Driver by die kampushek suksesvol IN of UIT scan, word die event outomaties voltooi en verdwyn.',
                          style: GoogleFonts.inter(color: kText2, fontSize: 11.5),
                        ),
                        const SizedBox(height: 18),
                        GradientActionButton(
                          label: _busy ? 'Skep...' : 'Aktiveer Saamry-event',
                          onTap: _busy ? () {} : _create,
                          height: 50,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class AddSaamryFriendPage extends StatefulWidget {
  const AddSaamryFriendPage({super.key});

  @override
  State<AddSaamryFriendPage> createState() => _AddSaamryFriendPageState();
}

class _AddSaamryFriendPageState extends State<AddSaamryFriendPage> {
  final TextEditingController _controller = TextEditingController();
  Timer? _debounce;
  bool _loading = false;
  int? _busyId;
  List<SaamryUserDto> _results = [];

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _searchChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () => _search(value));
  }

  Future<void> _search(String value) async {
    if (value.trim().length < 2) {
      if (mounted) setState(() => _results = []);
      return;
    }
    setState(() => _loading = true);
    try {
      final rows = await MoonApi.searchSaamryUsers(value);
      if (!mounted) return;
      setState(() {
        _results = rows;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
    }
  }

  Future<void> _send(SaamryUserDto user) async {
    setState(() => _busyId = user.gebruikerId);
    try {
      await MoonApi.sendSaamryFriendRequest(user.gebruikerId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Versoek aan ${user.volleNaam} gestuur')),
      );
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _busyId = null);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
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
            const AppScreenHeader(
              title: 'Voeg Vriend By',
              subtitle: 'Soek student of personeel',
              showBack: true,
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: TextField(
                controller: _controller,
                onChanged: _searchChanged,
                style: GoogleFonts.inter(color: kText1, fontSize: 13),
                decoration: InputDecoration(
                  hintText: 'Naam, van of nommer',
                  hintStyle: GoogleFonts.inter(color: kTextMuted, fontSize: 13),
                  prefixIcon: const Icon(Icons.search_rounded, color: kTextMuted),
                  filled: true,
                  fillColor: Colors.white.withOpacity(0.05),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),
            ),
            if (_loading) const LinearProgressIndicator(),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
                itemCount: _results.length,
                separatorBuilder: (_, __) => const SizedBox(height: 9),
                itemBuilder: (context, index) {
                  final user = _results[index];
                  final status = user.vriendskapStatus ?? 'GEEN';
                  final canAdd = status == 'GEEN' || status == 'GEWEIER';
                  return GlassCard(
                    padding: const EdgeInsets.all(13),
                    child: Row(
                      children: [
                        const Icon(Icons.person_rounded, color: kAccent),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                user.volleNaam,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Text(
                                '${user.rol} · ${user.nommer}',
                                style: const TextStyle(color: Colors.white54),
                              ),
                            ],
                          ),
                        ),
                        TextButton(
                          onPressed: !canAdd || _busyId == user.gebruikerId
                              ? null
                              : () => _send(user),
                          child: Text(
                            status == 'VRIEND'
                                ? 'Vriend'
                                : status.startsWith('HANGEND')
                                    ? 'Hangend'
                                    : _busyId == user.gebruikerId
                                        ? 'Stuur...'
                                        : 'Voeg By',
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class InviteSaamryFriendPage extends StatefulWidget {
  final int groepId;
  final List<SaamryFriendItemDto> friends;

  const InviteSaamryFriendPage({
    super.key,
    required this.groepId,
    required this.friends,
  });

  @override
  State<InviteSaamryFriendPage> createState() => _InviteSaamryFriendPageState();
}

class _InviteSaamryFriendPageState extends State<InviteSaamryFriendPage> {
  int? _busyId;

  Future<void> _invite(SaamryFriendItemDto friend) async {
    setState(() => _busyId = friend.gebruiker.gebruikerId);
    try {
      await MoonApi.inviteSaamryFriend(
        groepId: widget.groepId,
        gebruikerId: friend.gebruiker.gebruikerId,
      );
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _busyId = null);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
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
            const AppScreenHeader(
              title: 'Nooi Vriend',
              subtitle: 'Voeg by permanente groep',
              showBack: true,
            ),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: widget.friends.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  final friend = widget.friends[index];
                  return GlassCard(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        const Icon(Icons.person_add_alt_1, color: kAccent),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            friend.gebruiker.volleNaam,
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        TextButton(
                          onPressed: _busyId == friend.gebruiker.gebruikerId
                              ? null
                              : () => _invite(friend),
                          child: Text(
                            _busyId == friend.gebruiker.gebruikerId
                                ? 'Nooi...'
                                : 'Nooi',
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class SaamryChatPage extends StatefulWidget {
  final SaamryUserDto? friend;
  final SaamryGroupDto? group;

  const SaamryChatPage({
    super.key,
    this.friend,
    this.group,
  }) : assert((friend == null) != (group == null));

  @override
  State<SaamryChatPage> createState() => _SaamryChatPageState();
}

class _SaamryChatPageState extends State<SaamryChatPage> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  List<SaamryMessageDto> _messages = [];
  bool _loading = true;
  bool _sending = false;
  String? _error;
  WebSocket? _socket;
  StreamSubscription<dynamic>? _socketSub;
  Timer? _reconnectTimer;
  bool _disposed = false;

  static const _quick = <String>[
    'Waar moet ek jou optel?',
    'Ek is hier',
    'Ek is 5 min weg',
    'Ek wag by die hek',
  ];

  bool get _isGroup => widget.group != null;
  String get _title => _isGroup ? widget.group!.naam : widget.friend!.volleNaam;

  @override
  void initState() {
    super.initState();
    _loadInitial();
    _connectSocket();
  }

  @override
  void dispose() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _socketSub?.cancel();
    _socket?.close();
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  String _wsBase() {
    if (MoonApi.baseUrl.startsWith('https://')) {
      return MoonApi.baseUrl.replaceFirst('https://', 'wss://');
    }
    if (MoonApi.baseUrl.startsWith('http://')) {
      return MoonApi.baseUrl.replaceFirst('http://', 'ws://');
    }
    return MoonApi.baseUrl;
  }

  Future<void> _loadInitial() async {
    try {
      final rows = _isGroup
          ? await MoonApi.fetchSaamryGroupChat(widget.group!.groepId)
          : await MoonApi.fetchSaamryFriendChat(widget.friend!.gebruikerId);
      if (!mounted) return;
      setState(() {
        _messages = rows;
        _loading = false;
        _error = null;
      });
      _scrollBottom();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _connectSocket() async {
    if (_disposed) return;
    _reconnectTimer?.cancel();
    try {
      await _socketSub?.cancel();
      await _socket?.close();
    } catch (_) {}

    final token = MoonApi.bearerToken?.trim() ?? '';
    if (token.isEmpty) return;
    final path = _isGroup
        ? '/saamry/chat/ws/groep/${widget.group!.groepId}'
        : '/saamry/chat/ws/vriend/${widget.friend!.gebruikerId}';
    final uri = Uri.parse(
      '${_wsBase()}$path?token=${Uri.encodeQueryComponent(token)}',
    );

    try {
      final socket = await WebSocket.connect(uri.toString());
      if (_disposed) {
        await socket.close();
        return;
      }
      _socket = socket;
      _socketSub = socket.listen(
        _handleSocket,
        onDone: _scheduleReconnect,
        onError: (_) => _scheduleReconnect(),
        cancelOnError: false,
      );
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_disposed) return;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 2), _connectSocket);
  }

  void _handleSocket(dynamic raw) {
    try {
      final decoded = jsonDecode(raw.toString());
      if (decoded is! Map) return;
      if (decoded['tipe'] == 'FOUT') {
        if (mounted) setState(() => _error = decoded['fout']?.toString());
        return;
      }
      final rows = ((decoded['boodskappe'] as List?) ?? const [])
          .map((e) => SaamryMessageDto.fromJson(
                Map<String, dynamic>.from(e as Map),
              ))
          .toList();
      if (!mounted) return;
      setState(() {
        _messages = rows;
        _loading = false;
        _error = null;
      });
      _scrollBottom();
    } catch (_) {}
  }

  void _scrollBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
      );
    });
  }

  Future<void> _send([String? preset]) async {
    final text = (preset ?? _controller.text).trim();
    if (text.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
      if (_isGroup) {
        await MoonApi.sendSaamryGroupMessage(
          groepId: widget.group!.groepId,
          boodskap: text,
        );
      } else {
        await MoonApi.sendSaamryFriendMessage(
          friendId: widget.friend!.gebruikerId,
          boodskap: text,
        );
      }
      _controller.clear();
      await _loadInitial();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  String _time(DateTime? value) {
    if (value == null) return '';
    final local = value.toLocal();
    return '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }

  Widget _bubble(SaamryMessageDto message) {
    final mine = message.isMyne;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 310),
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.fromLTRB(12, 9, 12, 7),
        decoration: BoxDecoration(
          color: mine ? kAccent.withOpacity(0.20) : const Color(0xFF182235),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: mine ? kAccent.withOpacity(0.35) : Colors.white12,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (_isGroup && !mine)
              Padding(
                padding: const EdgeInsets.only(bottom: 3),
                child: Text(
                  message.stuurder?.volleNaam ?? 'Lid',
                  style: GoogleFonts.inter(
                    color: kAccent,
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            Text(
              message.boodskap,
              style: GoogleFonts.inter(color: kText1, fontSize: 13),
            ),
            const SizedBox(height: 3),
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                _time(message.geskepOp),
                style: GoogleFonts.inter(color: kTextMuted, fontSize: 9),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: _title,
              subtitle: _isGroup ? 'Permanente Saamrygroep' : 'Privaat Saamry-chat',
              showBack: true,
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                child: Text(
                  _error!,
                  style: const TextStyle(color: Colors.orangeAccent, fontSize: 11),
                ),
              ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                      itemCount: _messages.length,
                      itemBuilder: (_, index) => _bubble(_messages[index]),
                    ),
            ),
            SizedBox(
              height: 42,
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                scrollDirection: Axis.horizontal,
                itemCount: _quick.length,
                separatorBuilder: (_, __) => const SizedBox(width: 7),
                itemBuilder: (_, index) => ActionChip(
                  label: Text(_quick[index]),
                  onPressed: _sending ? null : () => _send(_quick[index]),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      minLines: 1,
                      maxLines: 4,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: 'Tik ’n boodskap...',
                        hintStyle: const TextStyle(color: Colors.white38),
                        filled: true,
                        fillColor: const Color(0xFF182235),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(18),
                          borderSide: BorderSide.none,
                        ),
                      ),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: _sending ? null : () => _send(),
                    icon: _sending
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send_rounded),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}


class _VisitorsTab extends StatefulWidget {
  const _VisitorsTab();

  @override
  State<_VisitorsTab> createState() => _VisitorsTabState();
}

class _VisitorsTabState extends State<_VisitorsTab> {
  final TextEditingController _naamController = TextEditingController();
  final TextEditingController _vanController = TextEditingController();
  final TextEditingController _selfoonController = TextEditingController();
  final TextEditingController _redeController = TextEditingController();

  bool _loading = true;
  bool _creating = false;
  String? _error;
  int? _busyInviteId;
  BesoekerUitnodigingDto? _latestInvite;
  List<BesoekerUitnodigingDto> _invites = [];

  @override
  void initState() {
    super.initState();
    _loadInvites();
  }

  @override
  void dispose() {
    _naamController.dispose();
    _vanController.dispose();
    _selfoonController.dispose();
    _redeController.dispose();
    super.dispose();
  }

  Future<void> _loadInvites() async {
    try {
      final invites = await MoonApi.fetchMyVisitorInvites();

      if (!mounted) return;

      setState(() {
        _invites = invites;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _loading = false;
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _createInvite() async {
    if (_creating) return;

    final naam = _naamController.text.trim();
    final van = _vanController.text.trim();
    final selfoon = _selfoonController.text.trim();
    final rede = _redeController.text.trim();

    if (naam.isEmpty || van.isEmpty || selfoon.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vul naam, van en selfoon in')),
      );
      return;
    }

    setState(() => _creating = true);

    try {
      final invite = await MoonApi.createVisitorInvite(
        naam: naam,
        van: van,
        selfoon: selfoon,
        rede: rede.isEmpty ? 'Besoek' : rede,
      );

      if (!mounted) return;

      setState(() {
        _creating = false;
        _latestInvite = invite;
        _invites = [
          invite,
          ..._invites.where(
            (item) => item.uitnodigingId != invite.uitnodigingId,
          ),
        ];
        _naamController.clear();
        _vanController.clear();
        _selfoonController.clear();
        _redeController.clear();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Colors.green,
          content: Text('Besoeker-uitnodiging is geskep'),
        ),
      );
    } catch (e) {
      if (!mounted) return;

      setState(() => _creating = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    }
  }

  Future<void> _copyOtp(BesoekerUitnodigingDto invite) async {
    await Clipboard.setData(ClipboardData(text: invite.otp));

    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('OTP is gekopieer')),
    );
  }

  Future<void> _shareInvite(
    BuildContext shareContext,
    BesoekerUitnodigingDto invite,
  ) async {
    final text = [
      'MOON Besoeker-uitnodiging',
      'Besoeker: ${invite.volleNaam}',
      'OTP: ${invite.otp}',
      'Geldig tot: ${_formatDateTime(invite.vervalOp)}',
      'Wys hierdie OTP by kampussekuriteit.',
    ].join('\n');

    final renderBox = shareContext.findRenderObject() as RenderBox?;

    await SharePlus.instance.share(
      ShareParams(
        text: text,
        subject: 'MOON Besoeker OTP',
        sharePositionOrigin: renderBox == null
            ? null
            : renderBox.localToGlobal(Offset.zero) & renderBox.size,
      ),
    );
  }

  Future<void> _cancelInvite(BesoekerUitnodigingDto invite) async {
    if (_busyInviteId != null) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: const Color(0xFF111827),
        title: const Text(
          'Kanselleer uitnodiging',
          style: TextStyle(color: Colors.white),
        ),
        content: Text(
          'Kanselleer ${invite.volleNaam} se OTP ${invite.otp}?',
          style: const TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Nee'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text(
              'Kanselleer OTP',
              style: TextStyle(color: Colors.red),
            ),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    setState(() => _busyInviteId = invite.uitnodigingId);

    try {
      final updated = await MoonApi.cancelVisitorInvite(
        invite.uitnodigingId,
      );

      if (!mounted) return;

      setState(() {
        _busyInviteId = null;
        _invites = _invites
            .map(
              (item) => item.uitnodigingId == updated.uitnodigingId
                  ? updated
                  : item,
            )
            .toList();

        if (_latestInvite?.uitnodigingId == updated.uitnodigingId) {
          _latestInvite = updated;
        }
      });
    } catch (e) {
      if (!mounted) return;

      setState(() => _busyInviteId = null);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    }
  }

  String _formatDateTime(DateTime value) {
    final day = value.day.toString().padLeft(2, '0');
    final month = value.month.toString().padLeft(2, '0');
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '$day/$month/${value.year} $hour:$minute';
  }

  String _statusLabel(BesoekerUitnodigingDto invite) {
    if (invite.isVerstreke) return 'VERVAL';
    switch (invite.status) {
      case 'TOEGELAAT':
        return 'TOEGELAAT';
      case 'GEWEIER':
        return 'GEWEIER';
      case 'GEKANSELLEER':
        return 'GEKANSELLEER';
      default:
        return 'HANGEND';
    }
  }

  Color _statusColor(BesoekerUitnodigingDto invite) {
    final status = _statusLabel(invite);
    switch (status) {
      case 'TOEGELAAT':
        return Colors.green;
      case 'GEWEIER':
      case 'GEKANSELLEER':
        return Colors.red;
      case 'VERVAL':
        return kTextMuted;
      default:
        return Colors.orange;
    }
  }

  Widget _inviteCard(BesoekerUitnodigingDto invite) {
    final pending = invite.isHangend;
    final busy = _busyInviteId == invite.uitnodigingId;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GlassCard(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.person_add_alt_1_rounded,
                  color: kAccent,
                  size: 26,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        invite.volleNaam,
                        style: GoogleFonts.inter(
                          color: kText1,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        invite.rede,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.inter(
                          color: kTextMuted,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Text(
                  _statusLabel(invite),
                  style: GoogleFonts.inter(
                    color: _statusColor(invite),
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 14,
              runSpacing: 6,
              children: [
                Text(
                  'OTP ${invite.otp}',
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1,
                  ),
                ),
                Text(
                  pending
                      ? 'Verval ${_formatDateTime(invite.vervalOp)}'
                      : 'Geskep ${_formatDateTime(invite.geskepOp)}',
                  style: GoogleFonts.inter(
                    color: kText2,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
            if (pending) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  TextButton.icon(
                    onPressed: () => _copyOtp(invite),
                    icon: const Icon(Icons.copy_rounded, size: 17),
                    label: const Text('Kopieer'),
                  ),
                  Builder(
                    builder: (shareContext) => TextButton.icon(
                      onPressed: () => _shareInvite(shareContext, invite),
                      icon: const Icon(Icons.share_rounded, size: 17),
                      label: const Text('Deel'),
                    ),
                  ),
                  TextButton.icon(
                    onPressed: busy ? null : () => _cancelInvite(invite),
                    icon: const Icon(
                      Icons.cancel_outlined,
                      size: 17,
                      color: Colors.red,
                    ),
                    label: Text(
                      busy ? 'Besig...' : 'Kanselleer',
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final activeCount = _invites.where((item) => item.isHangend).length;

    return RefreshIndicator(
      onRefresh: _loadInvites,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Besoekers',
              style: GoogleFonts.inter(
                color: kText1,
                fontSize: 22,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Nooi ’n besoeker en deel ’n eenmalige 6-syfer OTP.',
              style: GoogleFonts.inter(
                color: kTextMuted,
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '$activeCount van 5 aktiewe OTP’s',
              style: GoogleFonts.inter(
                color: activeCount >= 5 ? Colors.orange : kText2,
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 18),

            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'NOOI BESOEKER',
                    style: GoogleFonts.inter(
                      color: kTextMuted,
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.1,
                    ),
                  ),
                  const SizedBox(height: 14),
                  GlassInput(
                    controller: _naamController,
                    hintText: 'Naam',
                    prefixIcon: const Icon(
                      Icons.person,
                      color: kTextMuted,
                      size: 18,
                    ),
                  ),
                  const SizedBox(height: 10),
                  GlassInput(
                    controller: _vanController,
                    hintText: 'Van',
                    prefixIcon: const Icon(
                      Icons.person_outline,
                      color: kTextMuted,
                      size: 18,
                    ),
                  ),
                  const SizedBox(height: 10),
                  GlassInput(
                    controller: _selfoonController,
                    hintText: 'Selfoonnommer',
                    keyboardType: TextInputType.phone,
                    prefixIcon: const Icon(
                      Icons.phone,
                      color: kTextMuted,
                      size: 18,
                    ),
                  ),
                  const SizedBox(height: 10),
                  GlassInput(
                    controller: _redeController,
                    hintText: 'Rede vir besoek',
                    prefixIcon: const Icon(
                      Icons.description_outlined,
                      color: kTextMuted,
                      size: 18,
                    ),
                  ),
                  const SizedBox(height: 16),
                  GradientActionButton(
                    label: _creating
                        ? 'OTP WORD GESKEP...'
                        : activeCount >= 5
                            ? 'MAKSIMUM 5 AKTIEWE OTP’S'
                            : 'GENEREER OTP',
                    onTap: _creating || activeCount >= 5
                        ? () {}
                        : _createInvite,
                    height: 50,
                  ),
                ],
              ),
            ),

            if (_latestInvite != null) ...[
              const SizedBox(height: 16),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: _latestInvite!.isHangend
                      ? Colors.green.withOpacity(0.14)
                      : Colors.white10,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: _latestInvite!.isHangend
                        ? Colors.green
                        : Colors.white24,
                    width: 1.5,
                  ),
                ),
                child: Column(
                  children: [
                    Icon(
                      _latestInvite!.isHangend
                          ? Icons.check_circle
                          : Icons.info_outline,
                      color: _latestInvite!.isHangend
                          ? Colors.green
                          : kTextMuted,
                      size: 44,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _latestInvite!.isHangend
                          ? 'UITNODIGING GESKEP'
                          : _statusLabel(_latestInvite!),
                      style: GoogleFonts.inter(
                        color: _latestInvite!.isHangend
                            ? Colors.green
                            : _statusColor(_latestInvite!),
                        fontSize: 13,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.1,
                      ),
                    ),
                    const SizedBox(height: 14),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text(
                        _latestInvite!.otp,
                        style: GoogleFonts.inter(
                          color: kText1,
                          fontSize: 38,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 6,
                        ),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Geldig tot ${_formatDateTime(_latestInvite!.vervalOp)}',
                      style: GoogleFonts.inter(
                        color: kText2,
                        fontSize: 12,
                      ),
                    ),
                    if (_latestInvite!.isHangend) ...[
                      const SizedBox(height: 14),
                      Wrap(
                        alignment: WrapAlignment.center,
                        spacing: 10,
                        runSpacing: 8,
                        children: [
                          TextButton.icon(
                            onPressed: () => _copyOtp(_latestInvite!),
                            icon: const Icon(Icons.copy_rounded),
                            label: const Text('Kopieer OTP'),
                          ),
                          Builder(
                            builder: (shareContext) => TextButton.icon(
                              onPressed: () => _shareInvite(
                                shareContext,
                                _latestInvite!,
                              ),
                              icon: const Icon(Icons.share_rounded),
                              label: const Text('Deel OTP'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ],

            const SizedBox(height: 16),

            GlassCard(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'MY UITNODIGINGS',
                    style: GoogleFonts.inter(
                      color: kTextMuted,
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.1,
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (_loading)
                    const Center(
                      child: Padding(
                        padding: EdgeInsets.all(18),
                        child: CircularProgressIndicator(),
                      ),
                    )
                  else if (_error != null)
                    Column(
                      children: [
                        Text(
                          _error!,
                          textAlign: TextAlign.center,
                          style: GoogleFonts.inter(
                            color: Colors.red,
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 10),
                        OutlineActionButton(
                          label: 'Probeer Weer',
                          onTap: _loadInvites,
                          height: 44,
                        ),
                      ],
                    )
                  else if (_invites.isEmpty)
                    Text(
                      'Geen besoekers genooi nie',
                      style: GoogleFonts.inter(
                        color: kText2,
                        fontSize: 13,
                      ),
                    )
                  else
                    Column(
                      children: _invites
                          .map(_inviteCard)
                          .toList(),
                    ),
                ],
              ),
            ),
          ],
        ),
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
      _NavItem(icon: Icons.directions_car_rounded, label: 'Saamry'),
      _NavItem(icon: Icons.person_add_alt_1_rounded, label: 'Besoekers'),
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
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      items[i].label,
                      maxLines: 1,
                      style: GoogleFonts.inter(
                        color: active ? kText1 : kTextMuted,
                        fontSize: 10,
                        fontWeight:
                            active ? FontWeight.w600 : FontWeight.w400,
                      ),
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
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: ConstrainedBox(
                  constraints: BoxConstraints(
                    minHeight: MediaQuery.of(context).size.height -
                        MediaQuery.of(context).padding.top -
                        MediaQuery.of(context).padding.bottom -
                        140,
                  ),
                  child: IntrinsicHeight(
                    child: Row(
                      children: [
                        Expanded(
                          child: GlassTapPanel(
                            label: 'Kampus Skandering',
                            subtitle: 'Druk om te skandeer',
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
                            subtitle: 'Druk om te skandeer',
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
        _status = 'Hou jou foon teen die skandeerder';
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
    final screenHeight = MediaQuery.of(context).size.height;
    final screenWidth = MediaQuery.of(context).size.width;
    final qrSize = screenHeight < 620
        ? 110.0
        : screenHeight < 700
            ? 130.0
            : 170.0;
    final numberFontSize = screenWidth < 360 ? 32.0 : 38.0;

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Kampus Skandering',
              subtitle: 'Student',
              showBack: true,
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: GlassCard(
                  padding: const EdgeInsets.all(20),
                  child: Center(
                    child: _loading
                        ? const CircularProgressIndicator()
                        : Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(
                                Icons.nfc,
                                color: kAccent,
                                size: 56,
                              ),
                              const SizedBox(height: 14),
                              Text(
                                'Studentenommer',
                                style: GoogleFonts.inter(
                                  color: kTextMuted,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 8),
                              FittedBox(
                                child: Text(
                                  nommer,
                                  style: GoogleFonts.inter(
                                    color: kText1,
                                    fontSize: numberFontSize,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 2,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 14),
                              Text(
                                _status,
                                textAlign: TextAlign.center,
                                style: GoogleFonts.inter(
                                  color: kText2,
                                  fontSize: 14,
                                ),
                              ),
                              const SizedBox(height: 18),
                              GlassCard(
                                padding: const EdgeInsets.all(14),
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      'Alternatiewe QR-Kode',
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
                                        size: qrSize,
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
  bool _scanSukses = false;
  String _status = 'Druk om klas te skandeer';
  String? _laasteModule;
  String? _laasteLokaal;
  String? _laasteTyd;

  static const Map<String, int> _dagNommer = {
    'maandag': DateTime.monday,
    'monday': DateTime.monday,
    'dinsdag': DateTime.tuesday,
    'tuesday': DateTime.tuesday,
    'woensdag': DateTime.wednesday,
    'wednesday': DateTime.wednesday,
    'donderdag': DateTime.thursday,
    'thursday': DateTime.thursday,
    'vrydag': DateTime.friday,
    'friday': DateTime.friday,
    'saterdag': DateTime.saturday,
    'saturday': DateTime.saturday,
    'sondag': DateTime.sunday,
    'sunday': DateTime.sunday,
  };

  String _normaliseerUid(String value) => value.trim().toUpperCase();

  int? _tydNaMinute(String value) {
    final teks = value.trim().replaceAll('.', ':');
    final match = RegExp(r'^(\d{1,2}):(\d{2})').firstMatch(teks);
    if (match == null) return null;
    final uur = int.tryParse(match.group(1)!);
    final minuut = int.tryParse(match.group(2)!);
    if (uur == null || minuut == null || uur > 23 || minuut > 59) return null;
    return (uur * 60) + minuut;
  }

  bool _dagPas(StudentRoosterKlasDto klas, DateTime nou) {
    final dag = _dagNommer[klas.dag.trim().toLowerCase()];
    return dag == null || dag == nou.weekday;
  }

  bool _tydPas(StudentRoosterKlasDto klas, DateTime nou) {
    final begin = _tydNaMinute(klas.beginTyd);
    final einde = _tydNaMinute(klas.eindTyd);
    if (begin == null || einde == null) return false;

    final nouMinute = (nou.hour * 60) + nou.minute;
    if (einde > begin) {
      return nouMinute >= begin && nouMinute < einde;
    }

    // Ondersteun 'n klas wat oor middernag loop.
    return nouMinute >= begin || nouMinute < einde;
  }

  StudentRoosterKlasDto? _vindAktieweKlasVirUid(
    List<StudentRoosterKlasDto> rooster,
    String uid,
    DateTime nou,
  ) {
    final gesoek = _normaliseerUid(uid);
    for (final klas in rooster) {
      if (!_dagPas(klas, nou) || !_tydPas(klas, nou)) continue;
      final klasUid = _normaliseerUid(klas.nfcUid ?? '');
      if (klasUid.isNotEmpty && klasUid == gesoek) return klas;
    }
    return null;
  }

  String _roosterFout(
    List<StudentRoosterKlasDto> rooster,
    String uid,
    DateTime nou,
  ) {
    final gesoek = _normaliseerUid(uid);
    final aktief = rooster.where((klas) => _dagPas(klas, nou) && _tydPas(klas, nou)).toList();

    if (aktief.isEmpty) {
      return 'Jy het nie tans ’n geskeduleerde klas om in te skandeer nie.';
    }

    final selfdeTag = rooster.where((klas) {
      final klasUid = _normaliseerUid(klas.nfcUid ?? '');
      return klasUid.isNotEmpty && klasUid == gesoek;
    }).toList();

    if (selfdeTag.isNotEmpty) {
      return 'Hierdie lokaal is op jou rooster, maar nie vir die huidige klas-tyd nie.';
    }

    final klasNaam = aktief.first.vertoonNaam;
    final lokaal = aktief.first.vertoonLokaal;
    return 'Verkeerde lokaal. Jou huidige klas is $klasNaam in $lokaal.';
  }

  Future<String> _leesNdefUid(NfcTag tag) async {
    final ndef = Ndef.from(tag);
    if (ndef == null) return '';

    final message = await ndef.read();
    for (final record in message.records) {
      if (record.typeNameFormat != NdefTypeNameFormat.nfcWellknown ||
          String.fromCharCodes(record.type) != 'T') {
        continue;
      }

      final payload = record.payload;
      if (payload.isEmpty) continue;

      final languageCodeLength = payload.first & 0x3F;
      final textStart = 1 + languageCodeLength;
      if (textStart >= payload.length) continue;

      final value = utf8.decode(payload.sublist(textStart)).trim();
      if (value.isNotEmpty) return _normaliseerUid(value);
    }
    return '';
  }

  Future<void> _scanKlas() async {
    if (_busy) return;

    setState(() {
      _busy = true;
      _scanSukses = false;
      _laasteModule = null;
      _laasteLokaal = null;
      _laasteTyd = null;
      _status = 'Hou NFC tag teen toestel...';
    });

    try {
      final beskikbaar = await NfcManager.instance.isAvailable();
      if (!beskikbaar) {
        throw Exception('NFC is nie beskikbaar of aangeskakel op hierdie toestel nie.');
      }

      bool reedsHanteer = false;
      await NfcManager.instance.startSession(
        onDiscovered: (tag) async {
          if (reedsHanteer) return;
          reedsHanteer = true;

          try {
            final uid = await _leesNdefUid(tag);
            debugPrint('KLAS NFC UID GELEES = [$uid]');

            if (uid.isEmpty) {
              await NfcManager.instance.stopSession(
                errorMessage: 'Geen MOON NFC-kode op hierdie tag gevind nie',
              );
              if (!mounted) return;
              setState(() {
                _busy = false;
                _status = 'Geen MOON NFC-kode op hierdie tag gevind nie';
              });
              return;
            }

            if (mounted) {
              setState(() => _status = 'Kontroleer jou rooster...');
            }

            // Fail-closed: laat die BACKEND die fisiese tag na Lokasie_ID oplos
            // en dit teen die student se huidige roosterklas + SA-bedienertyd toets.
            // Dit vermy vals "verkeerde lokaal" foute weens UID-formatering of
            // die foon se plaaslike tyd. Geen geldige klas = geen ToegangsLog.
            final validasie = await MoonApi.valideerStudentKlasNfc(nfcUid: uid);

            final klasRaw = validasie['Klas'];
            if (klasRaw is! Map) {
              throw Exception('Die bediener kon nie die huidige klas bepaal nie.');
            }
            final klas = StudentRoosterKlasDto.fromJson(
              Map<String, dynamic>.from(klasRaw),
            );

            final kanoniekeUid = validasie['NFC_UID']?.toString().trim();
            if (kanoniekeUid == null || kanoniekeUid.isEmpty) {
              throw Exception('Die lokaal se NFC-kode ontbreek in die databasis.');
            }

            final result = await MoonApi.studentScanKlas(
              nfcUid: kanoniekeUid,
              rigting: 'IN',
            );

            await NfcManager.instance.stopSession();
            if (!mounted) return;

            final lokaal = result['LOK_Naam']?.toString().trim();
            final vertoonLokaal = lokaal != null && lokaal.isNotEmpty
                ? lokaal
                : (validasie['LOK_Naam']?.toString().trim().isNotEmpty == true
                    ? validasie['LOK_Naam'].toString().trim()
                    : klas.vertoonLokaal);

            DateTime nou = DateTime.now();
            final bedienerTyd = validasie['Bediener_Tyd']?.toString();
            if (bedienerTyd != null && bedienerTyd.isNotEmpty) {
              nou = DateTime.tryParse(bedienerTyd)?.toLocal() ?? nou;
            }
            final h = nou.hour.toString().padLeft(2, '0');
            final m = nou.minute.toString().padLeft(2, '0');

            setState(() {
              _busy = false;
              _scanSukses = true;
              _laasteModule = klas.vertoonNaam;
              _laasteLokaal = vertoonLokaal;
              _laasteTyd = '$h:$m';
              _status = 'Ingeskandeer vir ${klas.vertoonNaam}';
            });

            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                backgroundColor: Colors.green,
                content: Text(
                  '${klas.vertoonNaam} · $vertoonLokaal aangeteken',
                  style: const TextStyle(color: Colors.white),
                ),
              ),
            );
          } catch (e) {
            try {
              await NfcManager.instance.stopSession();
            } catch (_) {}

            if (!mounted) return;
            final fout = e.toString().replaceFirst('Exception: ', '');
            setState(() {
              _busy = false;
              _status = fout;
            });

            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                backgroundColor: Colors.red,
                content: Text(fout, style: const TextStyle(color: Colors.white)),
              ),
            );
          }
        },
      );
    } catch (e) {
      if (!mounted) return;
      final fout = e.toString().replaceFirst('Exception: ', '');
      setState(() {
        _busy = false;
        _status = fout;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(fout, style: const TextStyle(color: Colors.white)),
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
            const AppScreenHeader(
              title: 'Klas Skandering',
              subtitle: 'Student · NFC & Rooster',
              showBack: true,
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: ConstrainedBox(
                  constraints: BoxConstraints(
                    minHeight: MediaQuery.of(context).size.height -
                        MediaQuery.of(context).padding.top -
                        MediaQuery.of(context).padding.bottom -
                        140,
                  ),
                  child: GlassCard(
                    child: Center(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              _scanSukses ? Icons.check_circle_rounded : Icons.nfc,
                              color: _scanSukses ? Colors.green : kAccent,
                              size: 64,
                            ),
                            const SizedBox(height: 16),
                            Text(
                              _status,
                              textAlign: TextAlign.center,
                              style: GoogleFonts.inter(
                                color: _scanSukses ? Colors.green : kText1,
                                fontSize: 15,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            if (_scanSukses) ...[
                              const SizedBox(height: 18),
                              GlassCard(
                                padding: const EdgeInsets.all(14),
                                child: Column(
                                  children: [
                                    _KlasScanInfoRow(label: 'Klas', value: _laasteModule ?? '--'),
                                    const SizedBox(height: 8),
                                    _KlasScanInfoRow(label: 'Lokaal', value: _laasteLokaal ?? '--'),
                                    const SizedBox(height: 8),
                                    _KlasScanInfoRow(label: 'Tyd', value: _laasteTyd ?? '--'),
                                  ],
                                ),
                              ),
                            ],
                            const SizedBox(height: 20),
                            ElevatedButton.icon(
                              onPressed: _busy ? null : _scanKlas,
                              icon: _busy
                                  ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.nfc_rounded),
                              label: Text(_busy ? 'Besig...' : 'Skandeer Klas'),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'Die NFC-tag moet by die lokaal van jou huidige roosterklas geregistreer wees.',
                              textAlign: TextAlign.center,
                              style: GoogleFonts.inter(
                                color: kTextMuted,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),
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

class _KlasScanInfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _KlasScanInfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: 62,
          child: Text(
            label,
            style: GoogleFonts.inter(
              color: kTextMuted,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: GoogleFonts.inter(
              color: kText1,
              fontSize: 12,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    );
  }
}


// ─── EVENTS — inline binne student.dart ─────────────────────────────────────
class _StudentEventsPage extends StatefulWidget {
  const _StudentEventsPage({super.key});

  @override
  State<_StudentEventsPage> createState() => _StudentEventsPageState();
}

class _StudentEventsPageState extends State<_StudentEventsPage> {
  String _view = 'komende';
  bool _loading = true;
  int? _busyEventId;
  String? _error;
  List<MoonEventDto> _events = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await MoonApi.fetchEvents(view: _view);
      if (!mounted) return;
      setState(() {
        _events = result;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  Future<void> _setView(String value) async {
    if (_view == value) return;
    setState(() => _view = value);
    await _load();
  }

  Future<void> _rsvp(MoonEventDto event) async {
    if (_busyEventId != null) return;
    setState(() => _busyEventId = event.eventId);
    try {
      await MoonApi.rsvpEvent(event.eventId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('RSVP bevestig')),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    } finally {
      if (mounted) setState(() => _busyEventId = null);
    }
  }

  Future<void> _cancelRsvp(MoonEventDto event) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF111827),
        title: const Text('Kanselleer RSVP', style: TextStyle(color: Colors.white)),
        content: Text(
          'Kanselleer jou RSVP vir ${event.naam}?',
          style: const TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Nee'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Ja, kanselleer'),
          ),
        ],
      ),
    );
    if (yes != true || _busyEventId != null) return;
    setState(() => _busyEventId = event.eventId);
    try {
      await MoonApi.cancelEventRsvp(event.eventId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('RSVP gekanselleer')),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    } finally {
      if (mounted) setState(() => _busyEventId = null);
    }
  }

  String _date(DateTime dt) {
    const months = ['Jan', 'Feb', 'Mrt', 'Apr', 'Mei', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des'];
    return '${dt.day} ${months[dt.month - 1]} ${dt.year}';
  }

  String _time(DateTime dt) =>
      '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Events',
              subtitle: 'Komende events en RSVP',
              showBack: true,
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 6),
              child: Row(
                children: [
                  _StudentEventFilterButton(label: 'Komende', active: _view == 'komende', onTap: () => _setView('komende')),
                  const SizedBox(width: 8),
                  _StudentEventFilterButton(label: "My RSVP's", active: _view == 'my', onTap: () => _setView('my')),
                  const SizedBox(width: 8),
                  _StudentEventFilterButton(label: 'Vorige', active: _view == 'vorige', onTap: () => _setView('vorige')),
                ],
              ),
            ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: _load,
                child: _buildBody(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [SizedBox(height: 180), Center(child: CircularProgressIndicator())],
      );
    }
    if (_error != null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          const SizedBox(height: 80),
          const Icon(Icons.error_outline_rounded, color: Colors.red, size: 46),
          const SizedBox(height: 12),
          Text(_error!, textAlign: TextAlign.center, style: GoogleFonts.inter(color: Colors.red)),
        ],
      );
    }
    if (_events.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          const SizedBox(height: 80),
          const Icon(Icons.event_busy_rounded, color: kTextMuted, size: 52),
          const SizedBox(height: 12),
          Text(
            _view == 'my' ? "Jy het nog geen aktiewe RSVP's nie" : 'Geen events om te wys nie',
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(color: kText2, fontSize: 14),
          ),
        ],
      );
    }

    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
      itemCount: _events.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, index) {
        final event = _events[index];
        final busy = _busyEventId == event.eventId;
        return GlassCard(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.event_rounded, color: kAccent, size: 28),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(event.naam, style: GoogleFonts.inter(color: kText1, fontSize: 17, fontWeight: FontWeight.w800)),
                        const SizedBox(height: 4),
                        Text(
                          '${event.kampusNaam}${event.lokasieNaam == null ? '' : ' · ${event.lokasieNaam}'}',
                          style: GoogleFonts.inter(color: kText2, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  if (event.hetRsvp)
                    const Icon(Icons.check_circle_rounded, color: Colors.green, size: 24),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                '${_date(event.beginTyd)} · ${_time(event.beginTyd)}–${_time(event.eindTyd)}',
                style: GoogleFonts.inter(color: kText1, fontSize: 13, fontWeight: FontWeight.w600),
              ),
              if ((event.beskrywing ?? '').trim().isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(event.beskrywing!, maxLines: 3, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(color: kTextMuted, fontSize: 12)),
              ],
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      '${event.rsvpAantal} / ${event.kapasiteit} RSVP',
                      style: GoogleFonts.inter(color: event.vol ? Colors.orange : kText2, fontSize: 12, fontWeight: FontWeight.w700),
                    ),
                  ),
                  Text('${event.plekkeOor} plekke oor', style: GoogleFonts.inter(color: kTextMuted, fontSize: 11)),
                ],
              ),
              if (_view != 'vorige' && event.status == 'AKTIEF') ...[
                const SizedBox(height: 14),
                SizedBox(
                  width: double.infinity,
                  child: event.hetRsvp
                      ? OutlinedButton.icon(
                          onPressed: busy ? null : () => _cancelRsvp(event),
                          icon: const Icon(Icons.event_busy_rounded),
                          label: Text(busy ? 'Besig...' : 'Kanselleer RSVP'),
                        )
                      : ElevatedButton.icon(
                          onPressed: event.vol || busy ? null : () => _rsvp(event),
                          icon: const Icon(Icons.how_to_reg_rounded),
                          label: Text(event.vol ? 'EVENT VOL' : (busy ? 'Besig...' : 'RSVP – EK GAAN')),
                        ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _StudentEventFilterButton extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;

  const _StudentEventFilterButton({required this.label, required this.active, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
          decoration: BoxDecoration(
            color: active ? kAccent.withOpacity(0.14) : const Color(0x0AFFFFFF),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: active ? kAccent : const Color(0x14FFFFFF)),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: GoogleFonts.inter(color: active ? kText1 : kTextMuted, fontSize: 11, fontWeight: FontWeight.w700),
          ),
        ),
      ),
    );
  }
}
