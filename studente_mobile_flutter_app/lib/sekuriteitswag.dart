import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';

class SekuriteitswagHomePage extends StatefulWidget {
  const SekuriteitswagHomePage({super.key});

  @override
  State<SekuriteitswagHomePage> createState() => _SekuriteitswagHomePageState();
}

class _SekuriteitswagHomePageState extends State<SekuriteitswagHomePage> {
  String? _gekoseKampus = 'Hoofkampus';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Wagte',
              subtitle: _gekoseKampus ?? 'Kies kampus',
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: GlassCard(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: DropdownButton<String>(
                  value: _gekoseKampus,
                  dropdownColor: kBg,
                  isExpanded: true,
                  underline: const SizedBox(),
                  style: GoogleFonts.inter(color: kText1),
                  items: const [
                    DropdownMenuItem(value: 'Hoofkampus', child: Text('Hoofkampus')),
                    DropdownMenuItem(value: 'Koshuis', child: Text('Koshuis')),
                    DropdownMenuItem(value: 'Sportkampus', child: Text('Sportkampus')),
                  ],
                  onChanged: (value) => setState(() => _gekoseKampus = value),
                ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: GlassTapPanel(
                        label: 'Kampus Skandeer',
                        subtitle: 'IN / UIT',
                        icon: '🚪',
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => KampusSkandeerPage(
                                kampusNaam: _gekoseKampus ?? 'Hoofkampus',
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: GlassTapPanel(
                        label: 'Besoekers',
                        subtitle: 'OTP / Lisensie Foto',
                        icon: '👤',
                        borderColor: const Color(0x3300C2FF),
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => BesoekersPage(
                                kampusNaam: _gekoseKampus ?? 'Hoofkampus',
                              ),
                            ),
                          );
                        },
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

class KampusSkandeerPage extends StatelessWidget {
  final String kampusNaam;

  const KampusSkandeerPage({super.key, required this.kampusNaam});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Kampus Skandeer',
              subtitle: kampusNaam,
              showBack: true,
              trailing: const NfcStatusBadge(),
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
                              label: 'IN',
                              subtitle: 'Student kom in kampus',
                              icon: '⬇️',
                              onTap: () {},
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: GlassTapPanel(
                              label: 'UIT',
                              subtitle: 'Student verlaat kampus',
                              icon: '⬆️',
                              borderColor: const Color(0x3300C2FF),
                              onTap: () {},
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    GradientActionButton(
                      label: 'Gebruik QR Backup',
                      onTap: () {},
                      height: 48,
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

class BesoekersPage extends StatelessWidget {
  final String kampusNaam;

  const BesoekersPage({super.key, required this.kampusNaam});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Besoekers',
              subtitle: kampusNaam,
              showBack: true,
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  children: [
                    Expanded(
                      child: GlassTapPanel(
                        label: 'Beplande Besoeker',
                        subtitle: 'Voer OTP in',
                        icon: '🔐',
                        onTap: () {},
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: GlassTapPanel(
                        label: 'Onbeplande Besoeker',
                        subtitle: 'Neem lisensie foto',
                        icon: '📷',
                        borderColor: const Color(0x3300C2FF),
                        onTap: () {},
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