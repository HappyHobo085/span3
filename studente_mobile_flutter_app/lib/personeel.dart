import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'profile_page.dart';
import 'moon_api.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'dart:convert';
import 'dart:io';
import 'dart:async';
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


class PersoneelHomePage extends StatefulWidget {
  const PersoneelHomePage({super.key});

  @override
  State<PersoneelHomePage> createState() => _PersoneelHomePageState();
}

class _PersoneelHomePageState extends State<PersoneelHomePage> {
  int _selectedIndex = 0;

  void _openTab(int index) {
    if (!mounted) return;
    setState(() => _selectedIndex = index);
  }

  void _onNavTap(int index) {
    if (index == 1) {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => const PersoneelKampusInskanderingPage(),
        ),
      );
      return;
    }

    _openTab(index);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [NfcStatusBadge()],
              ),
            ),
            Expanded(
              child: _selectedIndex == 0
                  ? _TuisTab(
                      onSaamry: () => _openTab(2),
                      onVisitors: () => _openTab(3),
                    )
                  : _selectedIndex == 2
                      ? const _PersoneelSaamryTab()
                      : _selectedIndex == 3
                          ? const _VisitorsTab()
                          : const _ProfielTab(),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _PersoneelNavBar(
        selectedIndex: _selectedIndex,
        onTap: _onNavTap,
      ),
    );
  }
}

// ─── Personeel-dashboard ────────────────────────────────────────────────────
class _TuisTab extends StatefulWidget {
  final VoidCallback onSaamry;
  final VoidCallback onVisitors;

  const _TuisTab({
    required this.onSaamry,
    required this.onVisitors,
  });

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
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }

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
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  String _personeelNommer(Map<String, dynamic>? profile) {
    if (profile == null) return 'Geen personeelnommer';

    const keys = [
      'personeel_nommer',
      'PER_Nommer',
      'per_nommer',
      'Personeel_Nommer',
      'personeelNommer',
    ];

    for (final key in keys) {
      final value = profile[key]?.toString().trim();
      if (value != null && value.isNotEmpty) return value;
    }

    return 'Geen personeelnommer';
  }

  String _formatTime(dynamic value) {
    if (value == null) return 'Geen tyd';

    try {
      final dt = DateTime.parse(value.toString()).add(
        const Duration(hours: 2),
      );
      final hour = dt.hour.toString().padLeft(2, '0');
      final minute = dt.minute.toString().padLeft(2, '0');
      return '$hour:$minute';
    } catch (_) {
      return value.toString();
    }
  }

  String _valueFromMap(
    dynamic raw,
    List<String> keys, {
    String fallback = 'Onbekend',
  }) {
    if (raw is! Map) return fallback;

    for (final key in keys) {
      final value = raw[key]?.toString().trim();
      if (value != null && value.isNotEmpty) return value;
    }

    return fallback;
  }

  void _openQr() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => const PersoneelKampusInskanderingPage(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return RefreshIndicator(
        onRefresh: _loadDashboard,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(24),
          children: [
            const SizedBox(height: 120),
            const Icon(Icons.error_outline_rounded, color: Colors.red, size: 48),
            const SizedBox(height: 14),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(color: Colors.red, fontSize: 13),
            ),
            const SizedBox(height: 18),
            GradientActionButton(
              label: 'Probeer Weer',
              onTap: _loadDashboard,
              height: 48,
            ),
          ],
        ),
      );
    }

    final naam = _profile?['naam']?.toString().trim().isNotEmpty == true
        ? _profile!['naam'].toString().trim()
        : _profile?['GEB_Naam']?.toString().trim().isNotEmpty == true
            ? _profile!['GEB_Naam'].toString().trim()
            : 'Personeel';

    final personeelNommer = _personeelNommer(_profile);
    final kampusStatus = _dashboard?['kampus_status']?.toString() ?? 'ONBEKEND';
    final opKampus = kampusStatus == 'OP_KAMPUS';
    final laasteKampus = _dashboard?['laaste_kampus'];

    final lokasie = _valueFromMap(
      laasteKampus,
      const ['lokasie', 'LOK_Naam', 'naam'],
      fallback: 'Geen kampusskandering',
    );
    final rigting = _valueFromMap(
      laasteKampus,
      const ['rigting', 'TOE_Rigting', 'Rigting'],
      fallback: '',
    );
    final metode = _valueFromMap(
      laasteKampus,
      const ['metode', 'TOE_Metode', 'Metode'],
      fallback: '',
    );
    final tyd = laasteKampus is Map
        ? (laasteKampus['tyd'] ??
            laasteKampus['Tydstempel'] ??
            laasteKampus['TOE_Tydstempel'])
        : null;

    final detailParts = <String>[
      if (rigting.isNotEmpty) rigting,
      if (tyd != null) _formatTime(tyd),
      if (metode.isNotEmpty) metode,
    ];

    return RefreshIndicator(
      onRefresh: _loadDashboard,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Tuis',
              style: GoogleFonts.inter(
                color: kText1,
                fontSize: 22,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Personeel',
              style: GoogleFonts.inter(color: kTextMuted, fontSize: 12),
            ),
            const SizedBox(height: 18),

            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Row(
                children: [
                  const Icon(
                    Icons.badge_outlined,
                    color: kAccent,
                    size: 34,
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Welkom, $naam',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.inter(
                            color: kText1,
                            fontSize: 21,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          personeelNommer,
                          style: GoogleFonts.inter(
                            color: kText2,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
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
                    opKampus
                        ? Icons.check_circle_rounded
                        : Icons.cancel_rounded,
                    color: opKampus ? Colors.green : Colors.red,
                    size: 48,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    opKampus ? 'OP KAMPUS' : 'NIE OP KAMPUS',
                    textAlign: TextAlign.center,
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

            _PersoneelDashboardInfoCard(
              title: 'LAASTE KAMPUSSKANDERING',
              icon: Icons.location_on_outlined,
              mainText: lokasie,
              subText: detailParts.isEmpty
                  ? 'Nog geen IN/UIT-skandering nie'
                  : detailParts.join(' · '),
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
                final columns = available >= 820
                    ? 4
                    : available >= 430
                        ? 2
                        : 1;
                final tileWidth =
                    (available - ((columns - 1) * 12)) / columns;

                return Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    SizedBox(
                      width: tileWidth,
                      child: _PersoneelQuickAction(
                        icon: Icons.qr_code_2_rounded,
                        label: 'Wys QR',
                        subtitle: 'Kampustoegang',
                        onTap: _openQr,
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _PersoneelQuickAction(
                        icon: Icons.event_rounded,
                        label: 'Events',
                        subtitle: 'Komende events & RSVP',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const _PersoneelEventsPage()),
                        ),
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _PersoneelQuickAction(
                        icon: Icons.directions_car_rounded,
                        label: 'Saamry',
                        subtitle: 'Bestuur jou groep',
                        onTap: widget.onSaamry,
                      ),
                    ),
                    SizedBox(
                      width: tileWidth,
                      child: _PersoneelQuickAction(
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

class _PersoneelDashboardInfoCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final String mainText;
  final String subText;

  const _PersoneelDashboardInfoCard({
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
          Icon(icon, color: kAccent, size: 30),
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

class _PersoneelQuickAction extends StatelessWidget {
  final IconData icon;
  final String label;
  final String subtitle;
  final VoidCallback onTap;

  const _PersoneelQuickAction({
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
                    Text(
                      label,
                      style: GoogleFonts.inter(
                        color: kText1,
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
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
              const Icon(
                Icons.chevron_right_rounded,
                color: kTextMuted,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Saamry tab — backend-gekoppel, binne personeel.dart ─────────────────────

class _PersoneelSaamryTab extends StatefulWidget {
  const _PersoneelSaamryTab({super.key});

  @override
  State<_PersoneelSaamryTab> createState() => _PersoneelSaamryTabState();
}

class _PersoneelSaamryTabState extends State<_PersoneelSaamryTab> {
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
      MaterialPageRoute(builder: (_) => const _PersoneelCreateSaamryGroupPage()),
    );
    if (changed == true) await _load();
  }

  Future<void> _openAddFriend() async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const _PersoneelAddSaamryFriendPage()),
    );
    if (changed == true) await _load();
  }

  Future<void> _openDefaultPickup() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(builder: (_) => const SaamryDefaultPickupPage()),
    );
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
        builder: (_) => _PersoneelCreateSaamryEventPage(
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
        builder: (_) => _PersoneelInviteSaamryFriendPage(
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
        builder: (_) => _PersoneelSaamryChatPage(friend: friend.gebruiker),
      ),
    );
    await _load();
  }

  Future<void> _openGroupChat(SaamryGroupDto group) async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (_) => _PersoneelSaamryChatPage(group: group),
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
                      '$passengers passasier${passengers == 1 ? '' : 's'} · ${event.pickupGereed}/${event.pickupTotaal} adresse gereed',
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
                    : (myPinReady ? 'Pickup-kaart / Verander Adres' : 'Stel My Opteladres'),
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
              IconButton(
                tooltip: 'My pickup-adres',
                onPressed: _openDefaultPickup,
                icon: const Icon(Icons.location_on_rounded, color: kAccent),
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

class _PersoneelCreateSaamryGroupPage extends StatefulWidget {
  const _PersoneelCreateSaamryGroupPage({super.key});

  @override
  State<_PersoneelCreateSaamryGroupPage> createState() => _PersoneelCreateSaamryGroupPageState();
}

class _PersoneelCreateSaamryGroupPageState extends State<_PersoneelCreateSaamryGroupPage> {
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

class _PersoneelCreateSaamryEventPage extends StatefulWidget {
  final List<SaamryGroupDto> groups;
  final int? initialGroupId;

  const _PersoneelCreateSaamryEventPage({
    super.key,
    required this.groups,
    this.initialGroupId,
  });

  @override
  State<_PersoneelCreateSaamryEventPage> createState() => _PersoneelCreateSaamryEventPageState();
}

class _PersoneelCreateSaamryEventPageState extends State<_PersoneelCreateSaamryEventPage> {
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
    _loadDefaultDriverAddress();
  }

  Future<void> _loadDefaultDriverAddress() async {
    try {
      final profile = await MoonApi.fetchSaamryPickupProfile();
      if (!mounted || profile == null || _driverPin != null) return;
      setState(() {
        _driverPin = SaamryPinSelection(
          latitude: profile.latitude,
          longitude: profile.longitude,
          beskrywing: profile.beskrywing,
        );
      });
    } catch (_) {
      // 'n Gewone pickup-adres is gerieflik, maar nie nodig om die blad oop te maak nie.
    }
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
          title: 'Driver Beginadres',
          subtitle: _group.naam,
          initialLatitude: _driverPin?.latitude,
          initialLongitude: _driverPin?.longitude,
          initialBeskrywing: _driverPin?.beskrywing,
          allowSaveAsDefault: true,
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
        const SnackBar(content: Text('Stel eers die Driver se beginadres')),
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
        stoorDriverAsVerstek: _driverPin!.stoorAsVerstek,
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
                                ? 'Stel Driver se beginadres'
                                : 'Beginadres gereed · Verander',
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

class _PersoneelAddSaamryFriendPage extends StatefulWidget {
  const _PersoneelAddSaamryFriendPage({super.key});

  @override
  State<_PersoneelAddSaamryFriendPage> createState() => _PersoneelAddSaamryFriendPageState();
}

class _PersoneelAddSaamryFriendPageState extends State<_PersoneelAddSaamryFriendPage> {
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

class _PersoneelInviteSaamryFriendPage extends StatefulWidget {
  final int groepId;
  final List<SaamryFriendItemDto> friends;

  const _PersoneelInviteSaamryFriendPage({
    super.key,
    required this.groepId,
    required this.friends,
  });

  @override
  State<_PersoneelInviteSaamryFriendPage> createState() => _PersoneelInviteSaamryFriendPageState();
}

class _PersoneelInviteSaamryFriendPageState extends State<_PersoneelInviteSaamryFriendPage> {
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

class _PersoneelSaamryChatPage extends StatefulWidget {
  final SaamryUserDto? friend;
  final SaamryGroupDto? group;

  const _PersoneelSaamryChatPage({
    super.key,
    this.friend,
    this.group,
  }) : assert((friend == null) != (group == null));

  @override
  State<_PersoneelSaamryChatPage> createState() => _PersoneelSaamryChatPageState();
}

class _PersoneelSaamryChatPageState extends State<_PersoneelSaamryChatPage> {
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

// ─── Bottom nav ────────────────────────────────────────────────────────────────
class _PersoneelNavBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onTap;

  const _PersoneelNavBar({required this.selectedIndex, required this.onTap});

  @override
  Widget build(BuildContext context) {
    const items = [
      _NavItem(icon: Icons.home_rounded, label: 'Tuis'),
      _NavItem(icon: Icons.nfc_rounded, label: 'Kampus'),
      _NavItem(icon: Icons.directions_car_rounded, label: 'Saamry'),
      _NavItem(icon: Icons.person_add_alt_1_rounded, label: 'Besoekers'),
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


// ─── Kampus Inskandering ──────────────────────────────────────────────────────
class PersoneelKampusInskanderingPage extends StatefulWidget {
  const PersoneelKampusInskanderingPage({super.key});

  @override
  State<PersoneelKampusInskanderingPage> createState() =>
      _PersoneelKampusInskanderingPageState();
}

class _PersoneelKampusInskanderingPageState
    extends State<PersoneelKampusInskanderingPage> {
  bool _loading = true;
  String? _personeelNommer;
  String _status = 'Laai personeel profiel...';

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final profile = MoonApi.myProfile ?? await MoonApi.getMyProfile();

      if (!mounted) return;

      setState(() {
        _personeelNommer =
            profile['personeel_nommer']?.toString() ??
            profile['PER_Nommer']?.toString() ??
            profile['per_nommer']?.toString() ??
            profile['Personeel_Nommer']?.toString() ??
            profile['personeelNommer']?.toString();

        _loading = false;
        _status = 'Hou jou foon teen die skandeerder';
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _loading = false;
        _status = 'Kon nie personeelnommer laai nie';
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Fout: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final nommer = _personeelNommer ?? 'Onbekend';

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Kampus Skandering',
              subtitle: 'Personeel',
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
                                'Personeelnommer',
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




// ─── EVENTS — inline binne personeel.dart ───────────────────────────────────
class _PersoneelEventsPage extends StatefulWidget {
  const _PersoneelEventsPage({super.key});

  @override
  State<_PersoneelEventsPage> createState() => _PersoneelEventsPageState();
}

class _PersoneelEventsPageState extends State<_PersoneelEventsPage> {
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
                  _PersoneelEventFilterButton(label: 'Komende', active: _view == 'komende', onTap: () => _setView('komende')),
                  const SizedBox(width: 8),
                  _PersoneelEventFilterButton(label: "My RSVP's", active: _view == 'my', onTap: () => _setView('my')),
                  const SizedBox(width: 8),
                  _PersoneelEventFilterButton(label: 'Vorige', active: _view == 'vorige', onTap: () => _setView('vorige')),
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

class _PersoneelEventFilterButton extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;

  const _PersoneelEventFilterButton({required this.label, required this.active, required this.onTap});

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
