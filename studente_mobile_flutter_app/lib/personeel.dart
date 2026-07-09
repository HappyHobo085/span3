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

      setState(() {
        _personeelNommer =
            profile['personeel_nommer']?.toString() ??
            profile['PER_Nommer']?.toString() ??
            profile['per_nommer']?.toString() ??
            profile['Personeel_Nommer']?.toString();

        _loading = false;
        _status = 'Hou jou foon teen die skandeerder';
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _status = 'Kon nie personeel nommer laai nie';
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
            const AppScreenHeader(
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

// ─── Klas Bywoning ────────────────────────────────────────────────────────────
class KlasBywoningPage extends StatefulWidget {
  const KlasBywoningPage({super.key});

  @override
  State<KlasBywoningPage> createState() => _KlasBywoningPageState();
}

class _KlasBywoningPageState extends State<KlasBywoningPage> {
  String _selectedOpsie = 'Opsie 1';
  String _selectedFilter = 'Filtreer';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Klas Bywoning',
              subtitle: 'Personeel',
              showBack: true,
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    GlassSelect<String>(
                      value: _selectedOpsie,
                      items: ['Opsie 1', 'Opsie 2', 'Opsie 3']
                          .map((v) => DropdownMenuItem(
                              value: v,
                              child: Text(v,
                                  style: GoogleFonts.inter(
                                      color: kText1, fontSize: 12))))
                          .toList(),
                      onChanged: (v) {
                        if (v != null) setState(() => _selectedOpsie = v);
                      },
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        SizedBox(
                          width: 130,
                          child: GlassSelect<String>(
                            value: _selectedFilter,
                            items: ['Filtreer', 'Ander']
                                .map((v) => DropdownMenuItem(
                                    value: v,
                                    child: Text(v,
                                        style: GoogleFonts.inter(
                                            color: kText1, fontSize: 12))))
                                .toList(),
                            onChanged: (v) {
                              if (v != null)
                                setState(() => _selectedFilter = v);
                            },
                          ),
                        ),
                        const SizedBox(width: 10),
                        const Expanded(child: GlassSearchRow()),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Expanded(
                      child: GlassCard(
                        child: Center(
                          child: Text(
                            'Klas Bywoning Inligting',
                            style: GoogleFonts.inter(
                                color: kTextMuted, fontSize: 12),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        GradientActionButton(
                          label: 'Verfris',
                          onTap: () {},
                          width: 120,
                          height: 44,
                        ),
                        const SizedBox(width: 10),
                        OutlineActionButton(
                          label: 'Terug',
                          onTap: () => Navigator.pop(context),
                          width: 100,
                          height: 44,
                        ),
                      ],
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
