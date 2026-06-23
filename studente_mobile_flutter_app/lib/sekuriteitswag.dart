import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';
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

class KampusSkandeerPage extends StatefulWidget {
  final String kampusNaam;

  const KampusSkandeerPage({super.key, required this.kampusNaam});

  @override
  State<KampusSkandeerPage> createState() => _KampusSkandeerPageState();
}

class _KampusSkandeerPageState extends State<KampusSkandeerPage> {
  final TextEditingController _studentController = TextEditingController();
  bool _loading = false;
  Map<String, dynamic>? _studentResult;

  @override
  void dispose() {
    _studentController.dispose();
    super.dispose();
  }

  Future<void> _scanStudent(String rigting, String metode) async {
    final studentId = _studentController.text.trim();

    if (studentId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Voer eers student nommer of ID in')),
      );
      return;
    }

    setState(() {
      _loading = true;
      _studentResult = null;
    });

    try {
      final result = await MoonApi.wagteStudentScan(
        studentNomOrId: studentId,
        lokasieId: 1, // hardcode vir nou
        rigting: rigting,
        metode: metode,
      );

      setState(() {
        _studentResult = result;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Fout: $e')),
      );
    } finally {
      setState(() => _loading = false);
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
              title: 'Kampus Skandeer',
              subtitle: widget.kampusNaam,
              showBack: true,
              trailing: const NfcStatusBadge(),
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    GlassInput(
                      controller: _studentController,
                      hintText: 'Student nommer / ID',
                      prefixIcon: const Icon(
                        Icons.badge_outlined,
                        color: kTextMuted,
                        size: 18,
                      ),
                    ),
                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: GlassTapPanel(
                            label: 'IN',
                            subtitle: 'Student kom in kampus',
                            icon: '⬇️',
                            onTap: () => _scanStudent('IN', 'NFC'),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: GlassTapPanel(
                            label: 'UIT',
                            subtitle: 'Student verlaat kampus',
                            icon: '⬆️',
                            borderColor: const Color(0x3300C2FF),
                            onTap: () => _scanStudent('UIT', 'NFC'),
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 16),

                    GradientActionButton(
                      label: _loading ? 'Besig...' : 'Gebruik QR Backup',
                      onTap: _loading ? () {} : () => _scanStudent('IN', 'QR'),
                      height: 48,
                    ),

                    const SizedBox(height: 20),

                    if (_studentResult != null)
                      GlassCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            Text(
                              '${_studentResult!['naam']} ${_studentResult!['van']}',
                              style: GoogleFonts.inter(
                                color: kText1,
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Student Nr: ${_studentResult!['student_nommer']}',
                              style: GoogleFonts.inter(
                                color: kText2,
                                fontSize: 13,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              '${_studentResult!['rigting']} via ${_studentResult!['metode']}',
                              style: GoogleFonts.inter(
                                color: kSuccess,
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
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => BeplandeBesoekerOtpPage(
                                kampusNaam: kampusNaam,
                              ),
                            ),
                          );
                        },
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

class BeplandeBesoekerOtpPage extends StatefulWidget {
  final String kampusNaam;

  const BeplandeBesoekerOtpPage({
    super.key,
    required this.kampusNaam,
  });

  @override
  State<BeplandeBesoekerOtpPage> createState() =>
      _BeplandeBesoekerOtpPageState();
}

class _BeplandeBesoekerOtpPageState extends State<BeplandeBesoekerOtpPage> {
  final TextEditingController _otpController = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _otpController.dispose();
    super.dispose();
  }

  void _checkOtp() {
    final otp = _otpController.text.trim();

    if (otp.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Voer asseblief die OTP in')),
      );
      return;
    }

    setState(() => _loading = true);

    // Backend call kom volgende
    Future.delayed(const Duration(seconds: 1), () {
      setState(() => _loading = false);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('OTP ontvang: $otp')),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Beplande Besoeker',
              subtitle: widget.kampusNaam,
              showBack: true,
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    GlassInput(
                      controller: _otpController,
                      hintText: 'Voer OTP kode in',
                      keyboardType: TextInputType.number,
                      prefixIcon: const Icon(
                        Icons.lock_outline,
                        color: kTextMuted,
                        size: 18,
                      ),
                    ),
                    const SizedBox(height: 16),
                    GradientActionButton(
                      label: _loading ? 'Besig...' : 'Verifieer OTP',
                      onTap: _loading ? () {} : _checkOtp,
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