import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';

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
    if (index == 2) {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const KlasBywoningPage()),
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
class _PersoneelNavBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onTap;

  const _PersoneelNavBar({required this.selectedIndex, required this.onTap});

  @override
  Widget build(BuildContext context) {
    const items = [
      _NavItem(icon: Icons.home_rounded, label: 'Tuis'),
      _NavItem(icon: Icons.nfc_rounded, label: 'Kampus'),
      _NavItem(icon: Icons.people_rounded, label: 'Bywoning'),
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
class PersoneelKampusInskanderingPage extends StatelessWidget {
  const PersoneelKampusInskanderingPage({super.key});

  @override
  Widget build(BuildContext context) {
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
                child: Column(
                  children: [
                    Row(
                      children: [
                        GlassCard(
                          padding: const EdgeInsets.all(12),
                          radius: 12,
                          child: Column(
                            children: [
                              const Icon(Icons.nfc, color: kAccent, size: 24),
                              const SizedBox(height: 4),
                              Text('NFC',
                                  style: GoogleFonts.inter(
                                      color: kAccent,
                                      fontSize: 9,
                                      fontWeight: FontWeight.w700)),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        const NfcStatusBadge(),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        GradientActionButton(
                          label: 'Saam Ry',
                          onTap: () {},
                          width: 120,
                          height: 40,
                        ),
                        const SizedBox(width: 12),
                        const Expanded(child: GlassSearchRow()),
                      ],
                    ),
                    const SizedBox(height: 12),
                    const Expanded(child: GlassCard(child: SizedBox.expand())),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: GradientActionButton(
                            label: 'Skandeer In',
                            onTap: () {},
                            height: 44,
                          ),
                        ),
                        const SizedBox(width: 12),
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
