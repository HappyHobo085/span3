import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';

class OpsigterHomePage extends StatefulWidget {
  const OpsigterHomePage({super.key});

  @override
  State<OpsigterHomePage> createState() => _OpsigterHomePageState();
}

class _OpsigterHomePageState extends State<OpsigterHomePage> {
  int _selectedIndex = 0;

  void _onNavTap(int index) {
    if (index == 1) {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const _PlaceholderPage(title: 'Noodgevalle')),
      );
      return;
    }
    if (index == 2) {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const _OorsigPage()),
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
            const SizedBox(height: 10),
            Expanded(
              child: _selectedIndex == 0
                  ? const _TuisTab()
                  : const _ProfielTab(),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _OpsigterNavBar(
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
                        'Opsigter',
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
                  label: 'KAMPUSSE',
                  value: '3',
                  valueColor: kText1,
                  badge: '♦ Aktief',
                  badgeColor: kSuccess,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StatCard(
                  label: 'NOODGEVALLE',
                  value: '0',
                  valueColor: kAccent2,
                  badge: '♦ Vandag',
                  badgeColor: kSuccess,
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // Quick actions
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
            decoration: kGlassDecoration(radius: 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'VINNIGE TOEGANG',
                  style: GoogleFonts.inter(
                    color: kTextMuted,
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 12),
                _QuickActionRow(
                  label: 'Koshuis Oorsig',
                  icon: Icons.apartment_rounded,
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (_) =>
                            const _PlaceholderPage(title: 'Koshuis Oorsig')),
                  ),
                ),
                const _Divider(),
                _QuickActionRow(
                  label: 'Kampus Oorsig',
                  icon: Icons.location_city_rounded,
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (_) =>
                            const _PlaceholderPage(title: 'Kampus Oorsig')),
                  ),
                ),
                const _Divider(),
                _QuickActionRow(
                  label: 'Funksies Oorsig',
                  icon: Icons.event_rounded,
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (_) =>
                            const _PlaceholderPage(title: 'Funksies Oorsig')),
                  ),
                ),
                const _Divider(),
                _QuickActionRow(
                  label: 'Parkeer Spasie',
                  icon: Icons.local_parking_rounded,
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                        builder: (_) =>
                            const _PlaceholderPage(title: 'Parkeer Spasie')),
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

class _QuickActionRow extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;

  const _QuickActionRow({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Row(
          children: [
            Icon(icon, color: kAccent, size: 18),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                label,
                style: GoogleFonts.inter(
                  color: kText2,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            const Icon(Icons.chevron_right_rounded, color: kTextMuted, size: 18),
          ],
        ),
      ),
    );
  }
}

class _Divider extends StatelessWidget {
  const _Divider();

  @override
  Widget build(BuildContext context) =>
      const Divider(color: Color(0x0AFFFFFF), height: 1);
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

// ─── Oorsig page ──────────────────────────────────────────────────────────────
class _OorsigPage extends StatelessWidget {
  const _OorsigPage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Oorsig',
              subtitle: 'Opsigter',
              showBack: true,
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Expanded(
                      child: Row(
                        children: [
                          Expanded(
                            child: GlassTapPanel(
                              label: 'Koshuis Oorsig',
                              borderColor: const Color(0x3300C2FF),
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                    builder: (_) => const _PlaceholderPage(
                                        title: 'Koshuis Oorsig')),
                              ),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: GlassTapPanel(
                              label: 'Kampus Oorsig',
                              borderColor: const Color(0x3300C2FF),
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                    builder: (_) => const _PlaceholderPage(
                                        title: 'Kampus Oorsig')),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    Expanded(
                      child: Row(
                        children: [
                          Expanded(
                            child: GlassTapPanel(
                              label: 'Funksies Oorsig',
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                    builder: (_) => const _PlaceholderPage(
                                        title: 'Funksies Oorsig')),
                              ),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: GlassTapPanel(
                              label: 'Parkeer Spasie',
                              borderColor: const Color(0x3310B981),
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                    builder: (_) => const _PlaceholderPage(
                                        title: 'Parkeer Spasie')),
                              ),
                            ),
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

// ─── Placeholder page ─────────────────────────────────────────────────────────
class _PlaceholderPage extends StatelessWidget {
  final String title;
  const _PlaceholderPage({required this.title});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(title: title, subtitle: 'Opsigter', showBack: true),
            Expanded(
              child: Center(
                child: Text(
                  '$title\nBladsy is tans onder konstruksie',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(color: kTextMuted, fontSize: 14),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ─── Bottom nav ────────────────────────────────────────────────────────────────
class _OpsigterNavBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onTap;

  const _OpsigterNavBar({required this.selectedIndex, required this.onTap});

  @override
  Widget build(BuildContext context) {
    const items = [
      _NavItem(icon: Icons.home_rounded, label: 'Tuis'),
      _NavItem(icon: Icons.warning_amber_rounded, label: 'Noodgevalle'),
      _NavItem(icon: Icons.dashboard_rounded, label: 'Oorsig'),
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
