// Gebruik dieselfde imports bo, maar hou hierdie belangrikes:
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';
import 'dart:io';
import 'package:image_picker/image_picker.dart';
import 'package:nfc_manager/nfc_manager.dart';
import 'dart:convert';

// VERVANG NET die hele _KampusSkandeerPageState class met hierdie:
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
                    DropdownMenuItem(
                      value: 'Hoofkampus',
                      child: Text('Hoofkampus'),
                    ),
                    DropdownMenuItem(
                      value: 'Koshuis',
                      child: Text('Koshuis'),
                    ),
                    DropdownMenuItem(
                      value: 'Sportkampus',
                      child: Text('Sportkampus'),
                    ),
                  ],
                  onChanged: (value) {
                    setState(() => _gekoseKampus = value);
                  },
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
                              builder: (_) => const VisitorVerifyPage(),
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

  const KampusSkandeerPage({
    super.key,
    required this.kampusNaam,
  });

  @override
  State<KampusSkandeerPage> createState() => _KampusSkandeerPageState();
}
class _KampusSkandeerPageState extends State<KampusSkandeerPage> {
  final TextEditingController _studentController = TextEditingController();
  final FocusNode _scannerFocusNode = FocusNode();

  bool _loading = false;
  String _status = 'Klik IN of UIT en scan dan QR';
  String? _pendingRigting;
  Map<String, dynamic>? _studentResult;

  @override
  void dispose() {
    _studentController.dispose();
    _scannerFocusNode.dispose();
    super.dispose();
  }

  String _readNdefText(NfcTag tag) {
    String value = '';
    final ndef = Ndef.from(tag);

    if (ndef == null || ndef.cachedMessage == null) return value;

    for (final record in ndef.cachedMessage!.records) {
      if (record.typeNameFormat == NdefTypeNameFormat.nfcWellknown &&
          String.fromCharCodes(record.type) == 'T') {
        final payload = record.payload;
        if (payload.isNotEmpty) {
          final languageCodeLength = payload.first & 0x3F;
          value = utf8.decode(payload.sublist(1 + languageCodeLength)).trim();
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
      setState(() => _status = 'Geen nommer gelees nie');
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
        lokasieId: 1,
        rigting: rigting,
        metode: metode,
      );

      if (!mounted) return;

      setState(() {
          _studentResult = result;
          _studentController.clear();
          _pendingRigting = null;
          _status = 'SUKSES';
        });

        Future.delayed(const Duration(seconds: 5), () {
          if (!mounted) return;

          setState(() {
            _studentResult = null;
            _status = 'Klik IN of UIT en scan dan QR';
          });

          FocusScope.of(context).requestFocus(_scannerFocusNode);
        });
    } catch (e) {
      if (!mounted) return;
      setState(() => _status = 'Fout: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _startQrScan(String rigting) {
    setState(() {
      _pendingRigting = rigting;
      _studentController.clear();
      _studentResult = null;
      _status = 'Scan QR nou vir $rigting...';
    });

    Future.delayed(const Duration(milliseconds: 150), () {
      if (mounted) {
        FocusScope.of(context).requestFocus(_scannerFocusNode);
      }
    });
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
          final nommer = _readNdefText(tag);
          debugPrint('STUDENT NOMMER GELEES VIA NFC = [$nommer]');

          await NfcManager.instance.stopSession();

          if (!mounted) return;

          await _submitScan(
            nommer: nommer,
            rigting: rigting,
            metode: 'NFC',
          );
        },
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _status = 'NFC fout: $e';
      });
    }
  }

  void _handleScannerInput(String value) {
    final clean = value.trim();

    if (_pendingRigting == null || clean.isEmpty || _loading) return;

    final rigting = _pendingRigting!;
    _pendingRigting = null;

    _submitScan(
      nommer: clean,
      rigting: rigting,
      metode: 'QR',
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
                    TextField(
                      controller: _studentController,
                      focusNode: _scannerFocusNode,
                      autofocus: true,
                      keyboardType: TextInputType.none,
                      showCursor: false,
                      style: const TextStyle(color: Colors.transparent),
                      decoration: const InputDecoration(
                        border: InputBorder.none,
                        isCollapsed: true,
                        contentPadding: EdgeInsets.zero,
                      ),
                      onChanged: _handleScannerInput,
                      onSubmitted: _handleScannerInput,
                    ),

                    GlassCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          const Icon(Icons.qr_code_scanner, color: kAccent, size: 54),
                          const SizedBox(height: 12),
                          Text(
                            _status,
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: GradientActionButton(
                            label: _loading ? 'Besig...' : 'IN',
                            onTap: _loading ? () {} : () => _startQrScan('IN'),
                            height: 52,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: GradientActionButton(
                            label: _loading ? 'Besig...' : 'UIT',
                            onTap: _loading ? () {} : () => _startQrScan('UIT'),
                            height: 52,
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: GlassTapPanel(
                            label: _loading ? 'Besig...' : 'NFC IN',
                            subtitle: 'Toets later',
                            icon: '⬇️',
                            onTap: _loading ? () {} : () => _scanStudentNfc('IN'),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: GlassTapPanel(
                            label: _loading ? 'Besig...' : 'NFC UIT',
                            subtitle: 'Toets later',
                            icon: '⬆️',
                            borderColor: const Color(0x3300C2FF),
                            onTap: _loading ? () {} : () => _scanStudentNfc('UIT'),
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 20),

                  if (_studentResult != null)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: Colors.green.withOpacity(0.18),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: Colors.green,
                          width: 2,
                        ),
                      ),
                      child: Column(
                        children: [
                          const Icon(
                            Icons.check_circle,
                            color: Colors.green,
                            size: 60,
                          ),

                          const SizedBox(height: 10),

                          Text(
                            'STUDENT INGESCAN',
                            style: GoogleFonts.inter(
                              color: Colors.green,
                              fontSize: 20,
                              fontWeight: FontWeight.w800,
                            ),
                          ),

                          const SizedBox(height: 16),

                          if ((_studentResult!['foto_url'] ?? '')
                              .toString()
                              .isNotEmpty)
                            ClipRRect(
                              borderRadius: BorderRadius.circular(50),
                              child: Image.network(
                                '${MoonApi.baseUrl}${_studentResult!['foto_url']}',
                                width: 100,
                                height: 100,
                                fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) => const Icon(
                                  Icons.person,
                                  size: 90,
                                  color: kTextMuted,
                                ),
                              ),
                            )
                          else
                            const Icon(
                              Icons.person,
                              size: 90,
                              color: kTextMuted,
                            ),

                          const SizedBox(height: 12),

                          Text(
                            '${_studentResult!['naam']} ${_studentResult!['van']}',
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 22,
                              fontWeight: FontWeight.w700,
                            ),
                          ),

                          const SizedBox(height: 6),

                          Text(
                            'Student Nr: ${_studentResult!['student_nommer']}',
                            style: GoogleFonts.inter(
                              color: kText2,
                              fontSize: 15,
                            ),
                          ),

                          const SizedBox(height: 6),

                          Text(
                            '${_studentResult!['rigting']} via ${_studentResult!['metode']}',
                            style: GoogleFonts.inter(
                              color: Colors.green,
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
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

class VisitorVerifyPage extends StatefulWidget {
  const VisitorVerifyPage({super.key});

  @override
  State<VisitorVerifyPage> createState() => _VisitorVerifyPageState();
}

class _VisitorVerifyPageState extends State<VisitorVerifyPage> {
  final TextEditingController _otpController = TextEditingController();

  bool _verified = false;

  @override
  void dispose() {
    _otpController.dispose();
    super.dispose();
  }

  void _verifyOtp() {
    if (_otpController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Tik eers die OTP in')),
      );
      return;
    }

    setState(() {
      _verified = true;
    });
  }

  void _allowEntry() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        backgroundColor: Colors.green,
        content: Text(
          'Visitor entry allowed',
          style: TextStyle(color: Colors.white),
        ),
      ),
    );
  }

  void _denyEntry() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        backgroundColor: Colors.red,
        content: Text(
          'Visitor entry denied',
          style: TextStyle(color: Colors.white),
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
            const AppScreenHeader(
              title: 'Visitor OTP',
              subtitle: 'Verifieer besoeker',
              showBack: true,
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    GlassCard(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'VERIFY OTP',
                            style: GoogleFonts.inter(
                              color: kTextMuted,
                              fontSize: 9,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1.1,
                            ),
                          ),
                          const SizedBox(height: 14),
                          GlassInput(
                            controller: _otpController,
                            hintText: 'Tik visitor OTP',
                            keyboardType: TextInputType.number,
                            prefixIcon: const Icon(
                              Icons.password_rounded,
                              color: kTextMuted,
                              size: 18,
                            ),
                          ),
                          const SizedBox(height: 16),
                          GradientActionButton(
                            label: 'Verify OTP',
                            onTap: _verifyOtp,
                            height: 50,
                          ),
                        ],
                      ),
                    ),

                    if (_verified) ...[
                      const SizedBox(height: 18),

                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(18),
                        decoration: BoxDecoration(
                          color: Colors.green.withOpacity(0.14),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: Colors.green,
                            width: 1.5,
                          ),
                        ),
                        child: Column(
                          children: [
                            const Icon(
                              Icons.verified_rounded,
                              color: Colors.green,
                              size: 60,
                            ),

                            const SizedBox(height: 12),

                            Text(
                              'VALID VISITOR',
                              style: GoogleFonts.inter(
                                color: Colors.green,
                                fontSize: 13,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 1.1,
                              ),
                            ),

                            const SizedBox(height: 16),

                            Text(
                              'Connor Smith',
                              style: GoogleFonts.inter(
                                color: kText1,
                                fontSize: 22,
                                fontWeight: FontWeight.w800,
                              ),
                            ),

                            const SizedBox(height: 4),

                            Text(
                              'Invited by Steven Nel',
                              style: GoogleFonts.inter(
                                color: kTextMuted,
                                fontSize: 13,
                              ),
                            ),

                            const SizedBox(height: 16),

                            GlassCard(
                              padding: const EdgeInsets.all(14),
                              child: Column(
                                children: [
                                  _VisitorInfoRow(
                                    label: 'Reason',
                                    value: 'Meeting',
                                  ),
                                  const _VisitorDivider(),
                                  _VisitorInfoRow(
                                    label: 'OTP',
                                    value: _otpController.text.trim(),
                                  ),
                                  const _VisitorDivider(),
                                  const _VisitorInfoRow(
                                    label: 'Status',
                                    value: 'Waiting',
                                  ),
                                ],
                              ),
                            ),

                            const SizedBox(height: 18),

                            Row(
                              children: [
                                Expanded(
                                  child: GradientActionButton(
                                    label: 'Allow Entry',
                                    onTap: _allowEntry,
                                    height: 48,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: OutlineActionButton(
                                    label: 'Deny',
                                    onTap: _denyEntry,
                                    height: 48,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
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

class _VisitorInfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _VisitorInfoRow({
    required this.label,
    required this.value,
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
              color: kText1,
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _VisitorDivider extends StatelessWidget {
  const _VisitorDivider();

  @override
  Widget build(BuildContext context) {
    return const Divider(
      color: Color(0x0AFFFFFF),
      height: 1,
    );
  }
}