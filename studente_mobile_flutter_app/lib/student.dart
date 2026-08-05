import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';
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
    final dt = DateTime.parse(value.toString()).add(
      const Duration(hours: 2),
    );

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
                    label: 'Skandeer Klas',
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

// ─── Saamry tab — backend-gekoppel, binne student.dart ─────────────────────

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

  @override
  void initState() {
    super.initState();
    _load();
  }

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

  String _cleanError(Object error) {
    return error.toString().replaceFirst('Exception: ', '');
  }

  void _message(String message, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: error ? Colors.red : null,
        content: Text(message),
      ),
    );
  }

  Future<void> _runAction(
    Future<void> Function() action,
    String successMessage,
  ) async {
    if (_busy) return;
    setState(() => _busy = true);

    try {
      await action();
      if (!mounted) return;
      _message(successMessage);
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
    final result = await showDialog<bool>(
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
    );
    return result == true;
  }

  Future<void> _openCreateGroup() async {
    final created = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const CreateSaamryGroupPage()),
    );
    if (created == true) await _load();
  }

  Future<void> _openAddFriend() async {
    final sent = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const AddSaamryFriendPage()),
    );
    if (sent == true) await _load();
  }

  Future<void> _openInviteFriend(SaamryGroupDto group) async {
    final friends = _status?.friends ?? const <SaamryFriendItemDto>[];
    final existingIds = group.lede.map((e) => e.gebruiker.gebruikerId).toSet();
    final available = friends
        .where((friend) => !existingIds.contains(friend.gebruiker.gebruikerId))
        .toList();

    if (available.isEmpty) {
      _message('Geen beskikbare vriende om te nooi nie');
      return;
    }

    final invited = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => InviteSaamryFriendPage(
          groepId: group.groepId,
          friends: available,
        ),
      ),
    );
    if (invited == true) await _load();
  }

  String _formatDateTime(DateTime value) {
    final day = value.day.toString().padLeft(2, '0');
    final month = value.month.toString().padLeft(2, '0');
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '$day/$month/${value.year} · $hour:$minute';
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
            const SizedBox(height: 14),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(color: Colors.red, fontSize: 13),
            ),
            const SizedBox(height: 18),
            GradientActionButton(label: 'Probeer Weer', onTap: _load, height: 48),
          ],
        ),
      );
    }

    final status = _status!;

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
        children: [
          Text(
            'Saamry',
            style: GoogleFonts.inter(
              color: kText1,
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Skep ’n groep, voeg vriende by en bestuur uitnodigings.',
            style: GoogleFonts.inter(color: kTextMuted, fontSize: 12),
          ),

          if (status.incomingRequests.isNotEmpty) ...[
            const SizedBox(height: 18),
            _sectionTitle('VRIENDSKAPVERSOEKE'),
            const SizedBox(height: 8),
            ...status.incomingRequests.map(_incomingFriendCard),
          ],

          if (status.groupInvites.isNotEmpty) ...[
            const SizedBox(height: 18),
            _sectionTitle('SAAMRY-UITNODIGINGS'),
            const SizedBox(height: 8),
            ...status.groupInvites.map(_groupInviteCard),
          ],

          const SizedBox(height: 18),
          if (status.myGroup == null)
            _noGroupCard()
          else
            _activeGroupCard(status.myGroup!),

          const SizedBox(height: 18),
          _friendsCard(status),

          if (status.outgoingRequests.isNotEmpty) ...[
            const SizedBox(height: 16),
            _outgoingRequestsCard(status.outgoingRequests),
          ],
        ],
      ),
    );
  }

  Widget _sectionTitle(String text) {
    return Text(
      text,
      style: GoogleFonts.inter(
        color: kTextMuted,
        fontSize: 9,
        fontWeight: FontWeight.w800,
        letterSpacing: 1.1,
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
            _userRow(request.gebruiker),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: GradientActionButton(
                    label: _busy ? 'Besig...' : 'Aanvaar',
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
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.directions_car, color: kAccent, size: 28),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    group.naam,
                    style: GoogleFonts.inter(
                      color: kText1,
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _smallInfo(Icons.route, '${group.vertrekpunt} → ${group.bestemming}'),
            const SizedBox(height: 7),
            _smallInfo(Icons.schedule, _formatDateTime(group.vertrekTyd)),
            const SizedBox(height: 7),
            _smallInfo(Icons.person, 'Bestuurder: ${group.bestuurder.volleNaam}'),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: GradientActionButton(
                    label: 'Aanvaar',
                    onTap: _busy
                        ? () {}
                        : () => _runAction(
                              () async {
                                await MoonApi.acceptSaamryGroupInvite(group.groepId);
                              },
                              'Saamry-uitnodiging aanvaar',
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
                              'Uitnodiging geweier',
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

  Widget _noGroupCard() {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.directions_car_rounded, color: kAccent, size: 44),
          const SizedBox(height: 14),
          Text(
            'Geen aktiewe saamrygroep nie',
            style: GoogleFonts.inter(
              color: kText1,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Skep ’n groep as jy die bestuurder is, of aanvaar ’n uitnodiging.',
            style: GoogleFonts.inter(color: kText2, fontSize: 13),
          ),
          const SizedBox(height: 16),
          GradientActionButton(
            label: 'Skep Groep',
            onTap: _openCreateGroup,
            height: 50,
          ),
        ],
      ),
    );
  }

  Widget _activeGroupCard(SaamryGroupDto group) {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.check_circle, color: Colors.green, size: 27),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  group.naam,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 15),
          _infoRow('Status', group.status, valueColor: Colors.green),
          const Divider(color: Color(0x0AFFFFFF), height: 1),
          _infoRow('Bestuurder', group.bestuurder.volleNaam),
          const Divider(color: Color(0x0AFFFFFF), height: 1),
          _infoRow('Roete', '${group.vertrekpunt} → ${group.bestemming}'),
          const Divider(color: Color(0x0AFFFFFF), height: 1),
          _infoRow('Vertrek', _formatDateTime(group.vertrekTyd)),
          const Divider(color: Color(0x0AFFFFFF), height: 1),
          _infoRow(
            'Sitplekke oop',
            '${group.beskikbareSitplekke} van ${group.sitplekke}',
          ),

          const SizedBox(height: 16),
          _sectionTitle('GROEPLEDE'),
          const SizedBox(height: 10),
          ...group.lede.map((member) {
            final phone = member.gebruiker.selfoon;
            return Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                children: [
                  _avatar(member.gebruiker, size: 38),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          member.gebruiker.volleNaam,
                          style: GoogleFonts.inter(
                            color: kText1,
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        if (phone != null && phone.trim().isNotEmpty)
                          Text(
                            phone,
                            style: GoogleFonts.inter(
                              color: kTextMuted,
                              fontSize: 11,
                            ),
                          ),
                      ],
                    ),
                  ),
                  Text(
                    member.isBestuurder ? 'Bestuurder' : _statusLabel(member.status),
                    style: GoogleFonts.inter(
                      color: member.status == 'AANVAAR'
                          ? Colors.green
                          : Colors.orange,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            );
          }),

          const SizedBox(height: 8),
          if (group.isBestuurder) ...[
            GradientActionButton(
              label: 'Nooi Vriend',
              onTap: group.beskikbareSitplekke <= 0
                  ? () => _message('Die groep is vol')
                  : () => _openInviteFriend(group),
              height: 48,
            ),
            const SizedBox(height: 10),
            OutlineActionButton(
              label: _busy ? 'Besig...' : 'Sluit Groep',
              onTap: _busy
                  ? () {}
                  : () async {
                      final confirm = await _confirm(
                        title: 'Sluit Saamrygroep',
                        message: 'Is jy seker jy wil hierdie groep sluit?',
                        confirmLabel: 'Sluit',
                      );
                      if (!confirm) return;
                      await _runAction(
                        () => MoonApi.closeSaamryGroup(group.groepId),
                        'Saamrygroep is gesluit',
                      );
                    },
              height: 48,
            ),
          ] else
            OutlineActionButton(
              label: _busy ? 'Besig...' : 'Verlaat Groep',
              onTap: _busy
                  ? () {}
                  : () async {
                      final confirm = await _confirm(
                        title: 'Verlaat Saamrygroep',
                        message: 'Is jy seker jy wil die groep verlaat?',
                        confirmLabel: 'Verlaat',
                      );
                      if (!confirm) return;
                      await _runAction(
                        () => MoonApi.leaveSaamryGroup(group.groepId),
                        'Jy het die groep verlaat',
                      );
                    },
              height: 48,
            ),
        ],
      ),
    );
  }

  Widget _friendsCard(SaamryStatusDto status) {
    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: _sectionTitle('VRIENDE')),
              Text(
                status.friends.length.toString(),
                style: GoogleFonts.inter(
                  color: kAccent,
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (status.friends.isEmpty)
            Text(
              'Nog geen vriende nie',
              style: GoogleFonts.inter(color: kText2, fontSize: 13),
            )
          else
            ...status.friends.map((friend) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  children: [
                    _avatar(friend.gebruiker, size: 40),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            friend.gebruiker.volleNaam,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          Text(
                            '${friend.gebruiker.rol} · ${friend.gebruiker.nommer}',
                            style: GoogleFonts.inter(
                              color: kTextMuted,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      tooltip: 'Verwyder vriend',
                      icon: const Icon(Icons.person_remove_outlined, color: kTextMuted),
                      onPressed: _busy
                          ? null
                          : () async {
                              final confirm = await _confirm(
                                title: 'Verwyder Vriend',
                                message:
                                    'Verwyder ${friend.gebruiker.volleNaam} uit jou vriende?',
                                confirmLabel: 'Verwyder',
                              );
                              if (!confirm) return;
                              await _runAction(
                                () => MoonApi.removeSaamryFriend(
                                  friend.gebruiker.gebruikerId,
                                ),
                                'Vriend verwyder',
                              );
                            },
                    ),
                  ],
                ),
              );
            }),
          const SizedBox(height: 12),
          OutlineActionButton(
            label: 'Voeg Vriend By',
            onTap: _openAddFriend,
            height: 46,
          ),
        ],
      ),
    );
  }

  Widget _outgoingRequestsCard(List<SaamryFriendItemDto> requests) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _sectionTitle('HANGENDE VERSOEKE'),
          const SizedBox(height: 12),
          ...requests.map(
            (request) => Padding(
              padding: const EdgeInsets.only(bottom: 9),
              child: Row(
                children: [
                  const Icon(Icons.schedule, color: kTextMuted, size: 21),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      request.gebruiker.volleNaam,
                      style: GoogleFonts.inter(
                        color: kText2,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  Text(
                    'Hangend',
                    style: GoogleFonts.inter(
                      color: Colors.orange,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
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

  Widget _userRow(SaamryUserDto user) {
    return Row(
      children: [
        _avatar(user, size: 44),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                user.volleNaam,
                style: GoogleFonts.inter(
                  color: kText1,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                '${user.rol} · ${user.nommer}',
                style: GoogleFonts.inter(color: kTextMuted, fontSize: 11),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _avatar(SaamryUserDto user, {double size = 42}) {
    final foto = user.fotoUrl;
    if (foto != null && foto.isNotEmpty) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(size / 2),
        child: Image.network(
          '${MoonApi.baseUrl}$foto',
          width: size,
          height: size,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => Icon(
            Icons.person,
            color: kTextMuted,
            size: size * 0.8,
          ),
        ),
      );
    }
    return Icon(Icons.person, color: kTextMuted, size: size * 0.85);
  }

  Widget _smallInfo(IconData icon, String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: kTextMuted, size: 18),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            text,
            style: GoogleFonts.inter(color: kText2, fontSize: 12),
          ),
        ),
      ],
    );
  }

  Widget _infoRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 105,
            child: Text(
              label,
              style: GoogleFonts.inter(
                color: kTextMuted,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: GoogleFonts.inter(
                color: valueColor ?? kText1,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'AANVAAR':
        return 'Aanvaar';
      case 'HANGEND':
        return 'Hangend';
      case 'GEWEIER':
        return 'Geweier';
      default:
        return status;
    }
  }
}


class AddSaamryFriendPage extends StatefulWidget {
  const AddSaamryFriendPage({super.key});

  @override
  State<AddSaamryFriendPage> createState() => _AddSaamryFriendPageState();
}

class _AddSaamryFriendPageState extends State<AddSaamryFriendPage> {
  final TextEditingController _searchController = TextEditingController();
  bool _loading = false;
  int? _busyUserId;
  String? _error;
  List<SaamryUserDto> _results = [];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    final query = _searchController.text.trim();
    if (query.length < 2) {
      setState(() {
        _error = 'Tik minstens 2 karakters';
        _results = [];
      });
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final results = await MoonApi.searchSaamryUsers(query);
      if (!mounted) return;
      setState(() {
        _results = results;
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

  Future<void> _sendRequest(SaamryUserDto user) async {
    setState(() => _busyUserId = user.gebruikerId);
    try {
      await MoonApi.sendSaamryFriendRequest(user.gebruikerId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Versoek gestuur na ${user.volleNaam}')),
      );
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
      setState(() => _busyUserId = null);
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
              subtitle: 'Student of personeel',
              showBack: true,
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: GlassInput(
                controller: _searchController,
                hintText: 'Naam, nommer of ID-nommer',
                prefixIcon: const Icon(Icons.search, color: kTextMuted, size: 18),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: GradientActionButton(
                label: _loading ? 'Soek...' : 'Soek',
                onTap: _loading ? () {} : _search,
                height: 46,
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Text(
                              _error!,
                              textAlign: TextAlign.center,
                              style: GoogleFonts.inter(color: Colors.red, fontSize: 13),
                            ),
                          ),
                        )
                      : _results.isEmpty
                          ? Center(
                              child: Text(
                                'Soek vir ’n student of personeellid',
                                style: GoogleFonts.inter(color: kTextMuted, fontSize: 13),
                              ),
                            )
                          : ListView.separated(
                              padding: const EdgeInsets.all(16),
                              itemCount: _results.length,
                              separatorBuilder: (_, __) => const SizedBox(height: 10),
                              itemBuilder: (context, index) {
                                final user = _results[index];
                                return GlassCard(
                                  padding: const EdgeInsets.all(14),
                                  child: Row(
                                    children: [
                                      const Icon(Icons.person, color: kAccent, size: 34),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              user.volleNaam,
                                              style: GoogleFonts.inter(
                                                color: kText1,
                                                fontSize: 14,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                            const SizedBox(height: 3),
                                            Text(
                                              '${user.rol} · ${user.nommer}',
                                              style: GoogleFonts.inter(
                                                color: kTextMuted,
                                                fontSize: 11,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                      _relationshipButton(user),
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

  Widget _relationshipButton(SaamryUserDto user) {
    final status = user.vriendskapStatus ?? 'GEEN';
    if (status == 'VRIEND') {
      return const Text('Vriend', style: TextStyle(color: Colors.green));
    }
    if (status == 'HANGEND_UIT') {
      return const Text('Hangend', style: TextStyle(color: Colors.orange));
    }
    if (status == 'HANGEND_IN') {
      return const Text('Het jou genooi', style: TextStyle(color: Colors.orange));
    }

    final busy = _busyUserId == user.gebruikerId;
    return TextButton(
      onPressed: busy ? null : () => _sendRequest(user),
      child: Text(busy ? 'Stuur...' : 'Voeg by'),
    );
  }
}


class CreateSaamryGroupPage extends StatefulWidget {
  const CreateSaamryGroupPage({super.key});

  @override
  State<CreateSaamryGroupPage> createState() => _CreateSaamryGroupPageState();
}

class _CreateSaamryGroupPageState extends State<CreateSaamryGroupPage> {
  final _nameController = TextEditingController();
  final _fromController = TextEditingController();
  final _toController = TextEditingController();
  final _seatsController = TextEditingController(text: '3');

  DateTime _date = DateTime.now().add(const Duration(days: 1));
  TimeOfDay _time = const TimeOfDay(hour: 7, minute: 0);
  bool _busy = false;

  @override
  void dispose() {
    _nameController.dispose();
    _fromController.dispose();
    _toController.dispose();
    _seatsController.dispose();
    super.dispose();
  }

  String _dateLabel() {
    final d = _date.day.toString().padLeft(2, '0');
    final m = _date.month.toString().padLeft(2, '0');
    return '$d/$m/${_date.year}';
  }

  String _timeLabel() {
    final h = _time.hour.toString().padLeft(2, '0');
    final m = _time.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }

  Future<void> _pickDate() async {
    final selected = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (selected != null) setState(() => _date = selected);
  }

  Future<void> _pickTime() async {
    final selected = await showTimePicker(context: context, initialTime: _time);
    if (selected != null) setState(() => _time = selected);
  }

  Future<void> _create() async {
    final from = _fromController.text.trim();
    final to = _toController.text.trim();
    final seats = int.tryParse(_seatsController.text.trim());

    if (from.isEmpty || to.isEmpty) {
      _error('Vul vertrekpunt en bestemming in');
      return;
    }
    if (seats == null || seats < 1 || seats > 8) {
      _error('Sitplekke moet tussen 1 en 8 wees');
      return;
    }

    final departure = DateTime(
      _date.year,
      _date.month,
      _date.day,
      _time.hour,
      _time.minute,
    );

    setState(() => _busy = true);
    try {
      await MoonApi.createSaamryGroup(
        naam: _nameController.text,
        vertrekpunt: from,
        bestemming: to,
        vertrekTyd: departure,
        sitplekke: seats,
      );
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
              title: 'Skep Saamrygroep',
              subtitle: 'Ritbesonderhede',
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
                      _label('GROEPNAAM (OPSIONEEL)'),
                      const SizedBox(height: 8),
                      GlassInput(
                        controller: _nameController,
                        hintText: 'Byvoorbeeld: Leriba Oggendrit',
                        prefixIcon: const Icon(Icons.group, color: kTextMuted, size: 18),
                      ),
                      const SizedBox(height: 14),
                      _label('VERTREKPUNT'),
                      const SizedBox(height: 8),
                      GlassInput(
                        controller: _fromController,
                        hintText: 'Waar vertrek julle?',
                        prefixIcon: const Icon(Icons.trip_origin, color: kTextMuted, size: 18),
                      ),
                      const SizedBox(height: 14),
                      _label('BESTEMMING'),
                      const SizedBox(height: 8),
                      GlassInput(
                        controller: _toController,
                        hintText: 'Waarheen ry julle?',
                        prefixIcon: const Icon(Icons.location_on, color: kTextMuted, size: 18),
                      ),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Expanded(child: _pickerTile(Icons.calendar_month, 'Datum', _dateLabel(), _pickDate)),
                          const SizedBox(width: 10),
                          Expanded(child: _pickerTile(Icons.schedule, 'Tyd', _timeLabel(), _pickTime)),
                        ],
                      ),
                      const SizedBox(height: 14),
                      _label('PASSASIERSITPLEKKE'),
                      const SizedBox(height: 8),
                      GlassInput(
                        controller: _seatsController,
                        hintText: '1 tot 8',
                        keyboardType: TextInputType.number,
                        prefixIcon: const Icon(Icons.event_seat, color: kTextMuted, size: 18),
                      ),
                      const SizedBox(height: 20),
                      GradientActionButton(
                        label: _busy ? 'Skep...' : 'Skep Groep',
                        onTap: _busy ? () {} : _create,
                        height: 52,
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

  Widget _label(String text) {
    return Text(
      text,
      style: GoogleFonts.inter(
        color: kTextMuted,
        fontSize: 9,
        fontWeight: FontWeight.w800,
        letterSpacing: 1.1,
      ),
    );
  }

  Widget _pickerTile(
    IconData icon,
    String label,
    String value,
    VoidCallback onTap,
  ) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: Colors.white10,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white24),
        ),
        child: Column(
          children: [
            Icon(icon, color: kAccent, size: 23),
            const SizedBox(height: 6),
            Text(label, style: GoogleFonts.inter(color: kTextMuted, fontSize: 10)),
            const SizedBox(height: 3),
            Text(
              value,
              style: GoogleFonts.inter(
                color: kText1,
                fontSize: 13,
                fontWeight: FontWeight.w700,
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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${friend.gebruiker.volleNaam} is genooi')),
      );
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
      setState(() => _busyId = null);
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
              subtitle: 'Kies ’n passasier',
              showBack: true,
            ),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: widget.friends.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  final friend = widget.friends[index];
                  final busy = _busyId == friend.gebruiker.gebruikerId;
                  return GlassCard(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        const Icon(Icons.person_add_alt_1, color: kAccent, size: 28),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                friend.gebruiker.volleNaam,
                                style: GoogleFonts.inter(
                                  color: kText1,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Text(
                                '${friend.gebruiker.rol} · ${friend.gebruiker.nommer}',
                                style: GoogleFonts.inter(color: kTextMuted, fontSize: 11),
                              ),
                            ],
                          ),
                        ),
                        TextButton(
                          onPressed: busy ? null : () => _invite(friend),
                          child: Text(busy ? 'Nooi...' : 'Nooi'),
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
  String _status = 'Druk om klas te skandeer';

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
            debugPrint('UID WAT NA RUGSTEUN GESTUUR WORD = [$uid]');
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
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(
                            Icons.nfc,
                            color: kAccent,
                            size: 64,
                          ),
                          const SizedBox(height: 16),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            child: Text(
                              _status,
                              textAlign: TextAlign.center,
                              maxLines: 3,
                              overflow: TextOverflow.ellipsis,
                              style: GoogleFonts.inter(
                                color: kText1,
                                fontSize: 14,
                              ),
                            ),
                          ),
                          const SizedBox(height: 20),
                          ElevatedButton(
                            onPressed: _busy ? null : _scanKlas,
                            child: Text(
                              _busy
                                  ? 'Besig...'
                                  : 'Skandeer Klas',
                            ),
                          ),
                        ],
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
