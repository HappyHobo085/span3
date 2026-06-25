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
        _status = '${result['naam']} ${result['van']} ${result['rigting']}';
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
                      GlassCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          children: [
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
                              style: GoogleFonts.inter(color: kText2, fontSize: 13),
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
                              style: GoogleFonts.inter(color: kTextMuted, fontSize: 12),
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