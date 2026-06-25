import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';
import 'dart:io';
import 'package:image_picker/image_picker.dart';
import 'package:nfc_manager/nfc_manager.dart';
import 'dart:convert';
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
  String _status = 'Gereed om te skandeer';
  Map<String, dynamic>? _studentResult;

  @override
  void dispose() {
    _studentController.dispose();
    super.dispose();
  }

  String _readNdefText(NfcTag tag) {
    String value = '';

    final ndef = Ndef.from(tag);

    if (ndef == null || ndef.cachedMessage == null) {
      return value;
    }

    for (final record in ndef.cachedMessage!.records) {
      if (record.typeNameFormat == NdefTypeNameFormat.nfcWellknown &&
          String.fromCharCodes(record.type) == 'T') {
        final payload = record.payload;

        if (payload.isNotEmpty) {
          final languageCodeLength = payload.first & 0x3F;
          value = utf8.decode(
            payload.sublist(1 + languageCodeLength),
          ).trim();
        }
      }
    }

    return value;
  }

  Future<void> _submitScan({
    required String nommer,
    required String rigting,
    required String metode,
  }) async {
    final cleanNommer = nommer.trim();

    if (cleanNommer.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Geen studentenommer gelees nie')),
      );
      return;
    }

    setState(() {
      _loading = true;
      _studentResult = null;
      _status = 'Stuur na backend...';
    });

    try {
      final result = await MoonApi.wagteStudentScan(
        studentNomOrId: cleanNommer,
        lokasieId: 1, // hardcode hoofhek vir nou
        rigting: rigting,
        metode: metode,
      );

      if (!mounted) return;

      setState(() {
        _studentResult = result;
        _studentController.text = cleanNommer;
        _status = '${result['naam']} ${result['van']} ${result['rigting']}';
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _status = 'Fout';
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Fout: $e')),
      );
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _scanStudentNfc(String rigting) async {
    setState(() {
      _loading = true;
      _status = 'Hou student se foon teen MT90...';
      _studentResult = null;
    });

    try {
      await NfcManager.instance.startSession(
        onDiscovered: (tag) async {
          try {
            final nommer = _readNdefText(tag);

            debugPrint('STUDENT NOMMER GELEES VIA NFC = [$nommer]');

            await NfcManager.instance.stopSession();

            if (!mounted) return;

            await _submitScan(
              nommer: nommer,
              rigting: rigting,
              metode: 'NFC',
            );
          } catch (e) {
            await NfcManager.instance.stopSession(
              errorMessage: 'NFC leesfout',
            );

            if (!mounted) return;

            setState(() {
              _loading = false;
              _status = 'NFC leesfout';
            });

            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('NFC fout: $e')),
            );
          }
        },
      );
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _loading = false;
        _status = 'NFC kon nie begin nie';
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('NFC fout: $e')),
      );
    }
  }

  Future<void> _manualScan(String rigting, String metode) async {
    await _submitScan(
      nommer: _studentController.text,
      rigting: rigting,
      metode: metode,
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
                    GlassCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          const Icon(Icons.nfc, color: kAccent, size: 46),
                          const SizedBox(height: 12),
                          Text(
                            _status,
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 16),

                    GlassInput(
                      controller: _studentController,
                      hintText: 'Studentenommer backup bv. 111',
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
                            label: _loading ? 'Besig...' : 'NFC IN',
                            subtitle: 'Scan student se foon',
                            icon: '⬇️',
                            onTap: _loading ? () {} : () => _scanStudentNfc('IN'),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: GlassTapPanel(
                            label: _loading ? 'Besig...' : 'NFC UIT',
                            subtitle: 'Scan student se foon',
                            icon: '⬆️',
                            borderColor: const Color(0x3300C2FF),
                            onTap: _loading ? () {} : () => _scanStudentNfc('UIT'),
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: GradientActionButton(
                            label: 'Handmatig IN',
                            onTap: _loading ? () {} : () => _manualScan('IN', 'HANDMATIG'),
                            height: 46,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: GradientActionButton(
                            label: 'Handmatig UIT',
                            onTap: _loading ? () {} : () => _manualScan('UIT', 'HANDMATIG'),
                            height: 46,
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 20),

                    if (_studentResult != null)
                      GlassCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
                            if ((_studentResult!['foto_url'] ?? '').toString().isNotEmpty)
                              ClipRRect(
                                borderRadius: BorderRadius.circular(60),
                                child: Image.network(
                                  '${MoonApi.baseUrl}${_studentResult!['foto_url']}',
                                  width: 90,
                                  height: 90,
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) => const Icon(
                                    Icons.person,
                                    color: kTextMuted,
                                    size: 70,
                                  ),
                                ),
                              )
                            else
                              const Icon(Icons.person, color: kTextMuted, size: 70),

                            const SizedBox(height: 12),

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

                            const SizedBox(height: 6),

                            Text(
                              'Lokasie: ${_studentResult!['lokasie']}',
                              style: GoogleFonts.inter(
                                color: kTextMuted,
                                fontSize: 12,
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
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => OnbeplandeBesoekerPage(
                                kampusNaam: kampusNaam,
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

class OnbeplandeBesoekerPage extends StatefulWidget {
  final String kampusNaam;

  const OnbeplandeBesoekerPage({
    super.key,
    required this.kampusNaam,
  });

  @override
  State<OnbeplandeBesoekerPage> createState() => _OnbeplandeBesoekerPageState();
}

class _OnbeplandeBesoekerPageState extends State<OnbeplandeBesoekerPage> {
  final TextEditingController _redeController = TextEditingController();
  XFile? _lisensieFoto;

  @override
  void dispose() {
    _redeController.dispose();
    super.dispose();
  }

  Future<void> _neemFoto() async {
    final picker = ImagePicker();

    final foto = await picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 75,
    );

    if (foto == null) return;

    setState(() {
      _lisensieFoto = foto;
    });
  }

  void _stoorBesoeker() {
    if (_lisensieFoto == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Neem eers ’n lisensie foto')),
      );
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Onbeplande besoeker gereed om te stoor')),
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
              title: 'Onbeplande Besoeker',
              subtitle: widget.kampusNaam,
              showBack: true,
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    GlassInput(
                      controller: _redeController,
                      hintText: 'Rede bv. Delivery / Onderhoud',
                      prefixIcon: const Icon(
                        Icons.description_outlined,
                        color: kTextMuted,
                        size: 18,
                      ),
                    ),
                    const SizedBox(height: 16),

                    GlassCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          if (_lisensieFoto == null)
                            Text(
                              'Geen lisensie foto geneem nie',
                              style: GoogleFonts.inter(
                                color: kTextMuted,
                                fontSize: 13,
                              ),
                            )
                          else
                            ClipRRect(
                              borderRadius: BorderRadius.circular(12),
                              child: Image.file(
                                File(_lisensieFoto!.path),
                                height: 180,
                                width: double.infinity,
                                fit: BoxFit.cover,
                              ),
                            ),
                          const SizedBox(height: 16),
                          GradientActionButton(
                            label: 'Neem Lisensie Foto',
                            onTap: _neemFoto,
                            height: 46,
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 16),

                    GradientActionButton(
                      label: 'Stoor Besoeker',
                      onTap: _stoorBesoeker,
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