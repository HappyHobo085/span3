import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';

class SekuriteitswagHomePage extends StatefulWidget {
  const SekuriteitswagHomePage({super.key});

  @override
  State<SekuriteitswagHomePage> createState() => _SekuriteitswagHomePageState();
}

class _SekuriteitswagHomePageState extends State<SekuriteitswagHomePage> {
  int _selectedIndex = 0;

  void _onNavTap(int index) {
    if (index == 1) {
      Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => const _SkanderingPage()),
      );
      return;
    }
    if (index == 2) {
      Navigator.push(
        context,
        MaterialPageRoute(
            builder: (_) => const _PlaceholderPage(title: 'Rekords')),
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
      bottomNavigationBar: _SekuriteitNavBar(
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
                        'Sekuriteitswag',
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
                  label: 'INS VANDAG',
                  value: '24',
                  valueColor: kText1,
                  badge: '♦ Aktief',
                  badgeColor: kSuccess,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _StatCard(
                  label: 'BESOEKERS',
                  value: '3',
                  valueColor: kAccent2,
                  badge: '♦ Tans op kampus',
                  badgeColor: kAccent2,
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          // Scan prompt card
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 20),
            decoration: kGlassDecoration(radius: 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'SKANDEER TOEGANG',
                  style: GoogleFonts.inter(
                    color: kTextMuted,
                    fontSize: 9,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.2,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Skandeer Akademia Lede',
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'of Skandeer Besoeker',
                  style: GoogleFonts.inter(color: kText2, fontSize: 13),
                ),
                const SizedBox(height: 14),
                GradientActionButton(
                  label: 'Gaan na Skandeer',
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const _SkanderingPage()),
                  ),
                  height: 42,
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

// ─── Skandering selection page ────────────────────────────────────────────────
class _SkanderingPage extends StatelessWidget {
  const _SkanderingPage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Skandeer',
              subtitle: 'Sekuriteitswag',
              showBack: true,
              trailing: const NfcStatusBadge(),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: GlassTapPanel(
                        label: 'Skandeer Akademia Lede',
                        subtitle: 'Tap om te skandeer',
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const _PlaceholderPage(
                                  title: 'Skandeer Akademia lede')),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: GlassTapPanel(
                        label: 'Skandeer Besoeker',
                        subtitle: 'Tap om te skandeer',
                        borderColor: const Color(0x3300C2FF),
                        onTap: () => Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => const _PlaceholderPage(
                                  title: 'Skandeer Besoeker')),
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
            AppScreenHeader(title: title, showBack: true),
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
class _SekuriteitNavBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onTap;

  const _SekuriteitNavBar({required this.selectedIndex, required this.onTap});

  @override
  Widget build(BuildContext context) {
    const items = [
      _NavItem(icon: Icons.home_rounded, label: 'Tuis'),
      _NavItem(icon: Icons.nfc_rounded, label: 'Skandeer'),
      _NavItem(icon: Icons.history_rounded, label: 'Rekords'),
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
