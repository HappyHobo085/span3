import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'profile_page.dart';
import 'moon_api.dart';
import 'package:qr_flutter/qr_flutter.dart';

class PersoneelHomePage extends StatefulWidget {
  const PersoneelHomePage({super.key});

  @override
  State<PersoneelHomePage> createState() => _PersoneelHomePageState();
}

class _PersoneelHomePageState extends State<PersoneelHomePage> {
  int _selectedIndex = 0;

  void _onNavTap(int index) {
  if (index == 1) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const PersoneelKampusInskanderingPage()),
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
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [NfcStatusBadge()],
              ),
            ),
            Expanded(
              child: _selectedIndex == 0
                  ? const _TuisTab()
                  : _selectedIndex == 2
                      ? const _SaamryTab()
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

// ─── Tuis tab ─────────────────────────────────────────────────────────────────
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
                        'Personeel',
                        style: GoogleFonts.inter(color: kTextMuted, fontSize: 12),
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
                  label: 'STUDENTE',
                  value: '142',
                  valueColor: kText1,
                  badge: '♦ Vandag',
                  badgeColor: kSuccess,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StatCard(
                  label: 'BYWONING',
                  value: '87%',
                  valueColor: kAccent2,
                  badge: '♦ Hierdie week',
                  badgeColor: kAccent2,
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // Current class card
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
            decoration: kGlassDecoration(radius: 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'HUIDIGE KLAS',
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
                  style: GoogleFonts.inter(color: kText2, fontSize: 13),
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


class _SaamryTab extends StatefulWidget {
  const _SaamryTab();

  @override
  State<_SaamryTab> createState() => _SaamryTabState();
}

class _SaamryTabState extends State<_SaamryTab> {
  bool _groepAktief = false;

  final List<String> _friends = [];
  final List<String> _pendingRequests = [];
  final List<String> _passengers = [];

  void _createGroep() {
    setState(() {
      _groepAktief = true;
    });
  }

  void _sluitGroep() {
    setState(() {
      _groepAktief = false;
    });
  }

  void _placeholder(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  void _openAddFriendPage() async {
    final result = await Navigator.push<String>(
      context,
      MaterialPageRoute(
        builder: (_) => const AddFriendPage(),
      ),
    );

    if (result == null) return;

    setState(() {
      if (!_pendingRequests.contains(result)) {
        _pendingRequests.add(result);
      }
    });

    _placeholder('Vriendskapversoek gestuur na $result');
  }

  void _openInviteFriendPage() async {
    if (_friends.isEmpty) {
      _placeholder('Jy het nog geen vriende om te nooi nie');
      return;
    }

    final result = await Navigator.push<String>(
      context,
      MaterialPageRoute(
        builder: (_) => InviteFriendPage(friends: _friends),
      ),
    );

    if (result == null) return;

    setState(() {
      if (!_passengers.contains(result)) {
        _passengers.add(result);
      }
    });

    _placeholder('$result is suksesvol genooi');
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
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
          const SizedBox(height: 4),
          Text(
            'Skep ’n groep en nooi vriende om saam te ry.',
            style: GoogleFonts.inter(
              color: kTextMuted,
              fontSize: 12,
            ),
          ),

          const SizedBox(height: 18),

          if (!_groepAktief)
            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.directions_car_rounded,
                    color: kAccent,
                    size: 44,
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'Geen aktiewe saamry groep nie',
                    style: GoogleFonts.inter(
                      color: kText1,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Klik "Skep Groep" as jy die bestuurder is.',
                    style: GoogleFonts.inter(
                      color: kText2,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 16),
                  GradientActionButton(
                    label: 'Skep Groep',
                    onTap: _createGroep,
                    height: 50,
                  ),
                ],
              ),
            )
          else
            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(
                        Icons.check_circle,
                        color: kSuccess,
                        size: 26,
                      ),
                      const SizedBox(width: 10),
                      Text(
                        'My Saamry Groep',
                        style: GoogleFonts.inter(
                          color: kText1,
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 16),

                  _SaamryInfoRow(
                    label: 'Status',
                    value: 'Aktief',
                    valueColor: kSuccess,
                  ),
                  const _SaamryDivider(),
                  const _SaamryInfoRow(
                    label: 'Bestuurder',
                    value: 'Jy',
                  ),
                  const _SaamryDivider(),
                  _SaamryInfoRow(
                    label: 'Lede',
                    value: _passengers.length.toString(),
                  ),

                  if (_passengers.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(
                      'PASSASIERS',
                      style: GoogleFonts.inter(
                        color: kTextMuted,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.1,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Column(
                      children: _passengers
                          .map(
                            (name) => Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Row(
                                children: [
                                  const Icon(Icons.person, color: kAccent, size: 22),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      name,
                                      style: GoogleFonts.inter(
                                        color: kText1,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ),
                                  Text(
                                    'Genooi',
                                    style: GoogleFonts.inter(
                                      color: kTextMuted,
                                      fontSize: 11,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ],

                  const SizedBox(height: 18),

                  GradientActionButton(
                    label: 'Nooi Vriend',
                    onTap: _openInviteFriendPage,
                    height: 48,
                  ),

                  const SizedBox(height: 10),

                  OutlineActionButton(
                    label: 'Sluit Groep',
                    onTap: _sluitGroep,
                    height: 48,
                  ),
                ],
              ),
            ),

          const SizedBox(height: 16),

          GlassCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'VRIENDE',
                  style: GoogleFonts.inter(
                    color: kTextMuted,
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.1,
                  ),
                ),
                const SizedBox(height: 12),

                if (_friends.isEmpty)
                  Text(
                    'Nog geen vriende nie',
                    style: GoogleFonts.inter(
                      color: kText2,
                      fontSize: 13,
                    ),
                  )
                else
                  Column(
                    children: _friends
                        .map(
                          (friend) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Row(
                              children: [
                                const Icon(Icons.person, color: kAccent, size: 24),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    friend,
                                    style: GoogleFonts.inter(
                                      color: kText1,
                                      fontSize: 13,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        )
                        .toList(),
                  ),

                  if (_pendingRequests.isNotEmpty) ...[
                    const SizedBox(height: 14),
                    Text(
                      'HANGENDE VERSOEKE',
                      style: GoogleFonts.inter(
                        color: kTextMuted,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.1,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Column(
                      children: _pendingRequests
                          .map(
                            (friend) => Padding(
                              padding: const EdgeInsets.only(bottom: 10),
                              child: Row(
                                children: [
                                  const Icon(Icons.schedule, color: kTextMuted, size: 22),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      friend,
                                      style: GoogleFonts.inter(
                                        color: kText2,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ),
                                  TextButton(
                                    onPressed: () {
                                      setState(() {
                                        _pendingRequests.remove(friend);
                                        if (!_friends.contains(friend)) {
                                          _friends.add(friend);
                                        }
                                      });
                                    },
                                    child: const Text('Aanvaar'),
                                  ),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ],

                  const SizedBox(height: 16),

                  OutlineActionButton(
                    label: 'Voeg Vriend By',
                    onTap: _openAddFriendPage,
                    height: 46,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SaamryInfoRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? valueColor;

  const _SaamryInfoRow({
    required this.label,
    required this.value,
    this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: GoogleFonts.inter(
                color: kTextMuted,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Text(
            value,
            style: GoogleFonts.inter(
              color: valueColor ?? kText1,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _SaamryDivider extends StatelessWidget {
  const _SaamryDivider();

  @override
  Widget build(BuildContext context) {
    return const Divider(
      color: Color(0x0AFFFFFF),
      height: 1,
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

  String? _otp;
  final List<Map<String, String>> _invites = [];

  @override
  void dispose() {
    _naamController.dispose();
    _vanController.dispose();
    _selfoonController.dispose();
    _redeController.dispose();
    super.dispose();
  }

  void _generateOtp() {
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

    final generated = DateTime.now()
        .millisecondsSinceEpoch
        .toString()
        .substring(7, 13);

    setState(() {
      _otp = generated;
      _invites.insert(0, {
        'naam': '$naam $van',
        'selfoon': selfoon,
        'rede': rede.isEmpty ? 'Besoek' : rede,
        'otp': generated,
        'status': 'Waiting',
      });

      _naamController.clear();
      _vanController.clear();
      _selfoonController.clear();
      _redeController.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Visitors',
            style: GoogleFonts.inter(
              color: kText1,
              fontSize: 22,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Nooi ’n besoeker kampus toe en genereer ’n OTP.',
            style: GoogleFonts.inter(
              color: kTextMuted,
              fontSize: 12,
            ),
          ),

          const SizedBox(height: 18),

          GlassCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'INVITE VISITOR',
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
                  prefixIcon: const Icon(Icons.person, color: kTextMuted, size: 18),
                ),

                const SizedBox(height: 10),

                GlassInput(
                  controller: _vanController,
                  hintText: 'Van',
                  prefixIcon: const Icon(Icons.person_outline, color: kTextMuted, size: 18),
                ),

                const SizedBox(height: 10),

                GlassInput(
                  controller: _selfoonController,
                  hintText: 'Selfoonnommer',
                  keyboardType: TextInputType.phone,
                  prefixIcon: const Icon(Icons.phone, color: kTextMuted, size: 18),
                ),

                const SizedBox(height: 10),

                GlassInput(
                  controller: _redeController,
                  hintText: 'Rede vir besoek',
                  prefixIcon: const Icon(Icons.description_outlined, color: kTextMuted, size: 18),
                ),

                const SizedBox(height: 16),

                GradientActionButton(
                  label: 'Generate OTP',
                  onTap: _generateOtp,
                  height: 50,
                ),
              ],
            ),
          ),

          if (_otp != null) ...[
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: Colors.green.withOpacity(0.14),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.green, width: 1.5),
              ),
              child: Column(
                children: [
                  const Icon(Icons.check_circle, color: Colors.green, size: 44),
                  const SizedBox(height: 8),
                  Text(
                    'INVITE CREATED',
                    style: GoogleFonts.inter(
                      color: Colors.green,
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.1,
                    ),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    _otp!,
                    style: GoogleFonts.inter(
                      color: kText1,
                      fontSize: 38,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 6,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Share OTP with visitor',
                    style: GoogleFonts.inter(
                      color: kText2,
                      fontSize: 12,
                    ),
                  ),
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
                  'MY INVITES',
                  style: GoogleFonts.inter(
                    color: kTextMuted,
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.1,
                  ),
                ),

                const SizedBox(height: 12),

                if (_invites.isEmpty)
                  Text(
                    'Geen visitor invites nog nie',
                    style: GoogleFonts.inter(
                      color: kText2,
                      fontSize: 13,
                    ),
                  )
                else
                  Column(
                    children: _invites.map((invite) {
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Row(
                          children: [
                            const Icon(
                              Icons.person_add_alt_1_rounded,
                              color: kAccent,
                              size: 24,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    invite['naam']!,
                                    style: GoogleFonts.inter(
                                      color: kText1,
                                      fontSize: 13,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '${invite['rede']} · OTP ${invite['otp']}',
                                    style: GoogleFonts.inter(
                                      color: kTextMuted,
                                      fontSize: 11,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Text(
                              invite['status']!,
                              style: GoogleFonts.inter(
                                color: Colors.orange,
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
              ],
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


class AddFriendPage extends StatefulWidget {
  const AddFriendPage({super.key});

  @override
  State<AddFriendPage> createState() => _AddFriendPageState();
}

class _AddFriendPageState extends State<AddFriendPage> {
  final TextEditingController _searchController = TextEditingController();

  bool _loading = false;
  String? _error;
  List<StudentSearchDto> _results = [];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    final query = _searchController.text.trim();

    if (query.length < 2) {
      setState(() {
        _results = [];
        _error = null;
      });
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final results = await MoonApi.searchStudents(query);

      if (!mounted) return;

      setState(() {
        _results = results;
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

  void _sendRequest(StudentSearchDto student) {
    Navigator.pop(context, student.fullName);
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
              subtitle: 'Soek student',
              showBack: true,
            ),

            Padding(
              padding: const EdgeInsets.all(16),
              child: GlassInput(
                controller: _searchController,
                hintText: 'Soek naam, van of studentenommer',
                prefixIcon: const Icon(
                  Icons.search,
                  color: kTextMuted,
                  size: 18,
                ),
              ),
            ),

            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: GradientActionButton(
                label: 'Soek',
                onTap: _search,
                height: 46,
              ),
            ),

            const SizedBox(height: 12),

            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Text(
                            _error!,
                            style: GoogleFonts.inter(
                              color: Colors.red,
                              fontSize: 13,
                            ),
                          ),
                        )
                      : _results.isEmpty
                          ? Center(
                              child: Text(
                                'Geen studente gevind nie',
                                style: GoogleFonts.inter(
                                  color: kTextMuted,
                                  fontSize: 13,
                                ),
                              ),
                            )
                          : ListView.separated(
                              padding: const EdgeInsets.all(16),
                              itemCount: _results.length,
                              separatorBuilder: (_, __) =>
                                  const SizedBox(height: 10),
                              itemBuilder: (context, index) {
                                final student = _results[index];

                                return GlassCard(
                                  padding: const EdgeInsets.all(14),
                                  child: Row(
                                    children: [
                                      if ((student.fotoUrl ?? '').isNotEmpty)
                                        ClipRRect(
                                          borderRadius:
                                              BorderRadius.circular(24),
                                          child: Image.network(
                                            '${MoonApi.baseUrl}${student.fotoUrl}?v=${DateTime.now().millisecondsSinceEpoch}',
                                            width: 44,
                                            height: 44,
                                            fit: BoxFit.cover,
                                            errorBuilder: (_, __, ___) =>
                                                const Icon(
                                              Icons.person,
                                              color: kTextMuted,
                                              size: 34,
                                            ),
                                          ),
                                        )
                                      else
                                        const Icon(
                                          Icons.person,
                                          color: kTextMuted,
                                          size: 40,
                                        ),

                                      const SizedBox(width: 12),

                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              student.fullName,
                                              style: GoogleFonts.inter(
                                                color: kText1,
                                                fontSize: 14,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                            const SizedBox(height: 3),
                                            Text(
                                              student.studentNommer,
                                              style: GoogleFonts.inter(
                                                color: kTextMuted,
                                                fontSize: 11,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),

                                      TextButton(
                                        onPressed: () =>
                                            _sendRequest(student),
                                        child: const Text('Voeg by'),
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
class InviteFriendPage extends StatelessWidget {
  final List<String> friends;

  const InviteFriendPage({
    super.key,
    required this.friends,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Nooi Vriend',
              subtitle: 'Kies Vriend',
              showBack: true,
            ),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: friends.length,
                separatorBuilder: (_, __) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  final name = friends[index];

                  return GlassCard(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        const Icon(Icons.person_add_alt_1, color: kAccent, size: 28),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            name,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        TextButton(
                          onPressed: () => Navigator.pop(context, name),
                          child: const Text('Nooi'),
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
