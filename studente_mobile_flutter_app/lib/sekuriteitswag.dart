// Gebruik dieselfde imports bo, maar hou hierdie belangrikes:
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';
import 'dart:io';
import 'package:image_picker/image_picker.dart';
import 'package:nfc_manager/nfc_manager.dart';
import 'dart:convert';
import 'dart:async';

// VERVANG NET die hele _KampusSkandeerPageState class met hierdie:
class SekuriteitswagHomePage extends StatefulWidget {
  const SekuriteitswagHomePage({super.key});

  @override
  State<SekuriteitswagHomePage> createState() => _SekuriteitswagHomePageState();
}

class _SekuriteitswagHomePageState extends State<SekuriteitswagHomePage> {
  KampusDto? _gekoseKampus;
  List<KampusDto> _kampusse = [];
  bool _kampusseLoading = true;

  @override
  void initState() {
    super.initState();
    _loadKampusse();
  }

  Future<void> _loadKampusse() async {
    try {
      final kampusse = await MoonApi.fetchWagteKampusse();

      if (!mounted) return;

      setState(() {
        _kampusse = kampusse;
        _gekoseKampus = kampusse.isNotEmpty ? kampusse.first : null;
        _kampusseLoading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _kampusseLoading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Kon nie kampusse laai nie: $e')),
      );
    }
  }

  void _openKampusScan() {
    if (_gekoseKampus == null || _gekoseKampus!.kampusId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Kies eers ’n kampus')),
      );
      return;
    }

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => KampusSkandeerPage(
          kampusId: _gekoseKampus!.kampusId!,
          kampusNaam: _gekoseKampus!.naam,
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
            AppScreenHeader(
              title: 'Wagte',
              subtitle: _gekoseKampus?.naam ?? 'Kies kampus',
            ),

            Padding(
              padding: const EdgeInsets.all(16),
              child: GlassCard(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: _kampusseLoading
                    ? const Padding(
                        padding: EdgeInsets.all(14),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    : InkWell(
                        borderRadius: BorderRadius.circular(14),
                        onTap: () async {
                          final selected = await showMenu<KampusDto>(
                            context: context,
                            position: const RelativeRect.fromLTRB(16, 160, 16, 0),
                            color: kBg,
                            items: _kampusse.map((kampus) {
                              return PopupMenuItem<KampusDto>(
                                value: kampus,
                                child: Text(
                                  kampus.naam,
                                  style: GoogleFonts.inter(color: kText1),
                                ),
                              );
                            }).toList(),
                          );

                          if (selected != null) {
                            setState(() {
                              _gekoseKampus = selected;
                            });
                          }
                        },
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 14),
                          child: Row(
                            children: [
                              Expanded(
                                child: Text(
                                  _gekoseKampus?.naam ?? 'Kies kampus',
                                  style: GoogleFonts.inter(color: kText1),
                                ),
                              ),
                              const Icon(
                                Icons.keyboard_arrow_down_rounded,
                                color: kTextMuted,
                              ),
                            ],
                          ),
                        ),
                      ),
              ),
            ),

            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: GlassTapPanel(
                            label: 'Kampus Skandeer',
                            subtitle: 'IN / UIT',
                            icon: '🚪',
                            onTap: _openKampusScan,
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: GlassTapPanel(
                            label: 'Besoekers',
                            subtitle: 'OTP verifieer',
                            icon: '👤',
                            borderColor: const Color(0x3300C2FF),
                            onTap: () {
                              if (_gekoseKampus == null ||
                                  _gekoseKampus!.kampusId == null) {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                    content: Text('Kies eers ’n kampus'),
                                  ),
                                );
                                return;
                              }

                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => VisitorVerifyPage(
                                    kampusId: _gekoseKampus!.kampusId!,
                                    kampusNaam: _gekoseKampus!.naam,
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    GlassTapPanel(
                      label: 'Onverwagte Besoeker',
                      subtitle: 'Neem lisensie foto en rede',
                      icon: '📷',
                      borderColor: const Color(0x3300C2FF),
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const OnverwagteBesoekerPage(),
                          ),
                        );
                      },
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
  final int kampusId;
  final String kampusNaam;

  const KampusSkandeerPage({
    super.key,
    required this.kampusId,
    required this.kampusNaam,
  });

  @override
  State<KampusSkandeerPage> createState() => _KampusSkandeerPageState();
}
class _KampusSkandeerPageState extends State<KampusSkandeerPage> {
  // Die MT90 se QR-skandeerder werk soos 'n fisiese sleutelbord.
  // Hierdie versteekte veld bly gefokus om QR-kodes outomaties te ontvang.
  final TextEditingController _scannerController = TextEditingController();
  final FocusNode _scannerFocusNode = FocusNode();

  // Sigbare veld heel bo vir handmatige invoer.
  final TextEditingController _manualController = TextEditingController();
  final FocusNode _manualFocusNode = FocusNode();

  Timer? _qrDebounce;
  Timer? _manualDebounce;
  bool _manualChecking = false;
  bool? _manualNommerBestaan;
  bool _manualNommerAktief = true;
  String? _manualNommerTipe;
  String? _manualNommerNaam;
  bool _loading = false;
  bool _nfcSessionActive = false;
  bool _nfcAvailable = false;
  String _status = 'Gereed – skandeer QR of hou NFC-tag teen die toestel';

  @override
  void initState() {
    super.initState();

    _manualFocusNode.addListener(() {
      if (!_manualFocusNode.hasFocus && !_loading) {
        _focusQrScanner();
      }
    });

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      _focusQrScanner();
      await _startNfcListening();
    });
  }

  @override
  void dispose() {
    _qrDebounce?.cancel();
    _manualDebounce?.cancel();

    // Moenie dispose vertraag deur hier te await nie.
    if (_nfcSessionActive) {
      NfcManager.instance.stopSession().catchError((_) {});
    }

    _scannerController.dispose();
    _scannerFocusNode.dispose();
    _manualController.dispose();
    _manualFocusNode.dispose();
    super.dispose();
  }

  void _focusQrScanner() {
    if (!mounted || _loading || _manualFocusNode.hasFocus) return;

    Future.delayed(const Duration(milliseconds: 120), () {
      if (!mounted || _loading || _manualFocusNode.hasFocus) return;
      _scannerFocusNode.requestFocus();
    });
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
          value = utf8
              .decode(payload.sublist(1 + languageCodeLength))
              .trim();
        }
      }
    }

    return value;
  }

  Future<void> _startNfcListening() async {
    if (!mounted || _loading || _nfcSessionActive) return;

    try {
      final available = await NfcManager.instance.isAvailable();

      if (!mounted) return;

      setState(() {
        _nfcAvailable = available;
      });

      if (!available) return;

      _nfcSessionActive = true;

      await NfcManager.instance.startSession(
        onDiscovered: (tag) async {
          if (_loading) return;

          final nommer = _readNdefText(tag);
          debugPrint('NOMMER GELEES VIA NFC = [$nommer]');

          await _stopNfcListening();

          if (!mounted) return;

          if (nommer.trim().isEmpty) {
            setState(() {
              _status = 'NFC-tag bevat nie ’n leesbare nommer nie';
            });
            await _resumeAutomaticListening();
            return;
          }

          await _submitScan(
            nommer: nommer,
            metode: 'NFC',
          );
        },
      );
    } catch (e) {
      _nfcSessionActive = false;

      if (!mounted) return;

      setState(() {
        _nfcAvailable = false;
        _status = 'QR en handmatige invoer gereed – NFC is nie beskikbaar nie';
      });
    }
  }

  Future<void> _stopNfcListening() async {
    if (!_nfcSessionActive) return;

    try {
      await NfcManager.instance.stopSession();
    } catch (_) {
      // Die sessie kan reeds deur Android gestop wees.
    } finally {
      _nfcSessionActive = false;
    }
  }

  Future<void> _resumeAutomaticListening() async {
    if (!mounted) return;

    _scannerController.clear();
    _focusQrScanner();
    await _startNfcListening();
  }

  Future<void> _submitScan({
    required String nommer,
    required String metode,
  }) async {
    final cleanNommer = nommer.trim();

    if (cleanNommer.isEmpty || _loading) return;

    _qrDebounce?.cancel();
    await _stopNfcListening();

    if (!mounted) return;

    _scannerFocusNode.unfocus();
    _manualFocusNode.unfocus();
    FocusScope.of(context).unfocus();

    setState(() {
      _loading = true;
      _status = metode == 'NFC'
          ? 'NFC gelees – profiel laai...'
          : metode == 'QR'
              ? 'QR gelees – profiel laai...'
              : 'Nommer ingevoer – profiel laai...';
    });

    try {
      final profile = await MoonApi.wagteProfileScan(cleanNommer);

      if (!mounted) return;

      _scannerController.clear();
      if (metode == 'HANDMATIG') {
        _manualDebounce?.cancel();
        _manualController.clear();
        _manualChecking = false;
        _manualNommerBestaan = null;
        _manualNommerAktief = true;
        _manualNommerTipe = null;
        _manualNommerNaam = null;
      }

      setState(() {
        _loading = false;
        _status = 'Profiel gevind via $metode';
      });

      final saamryPreview = await MoonApi.wagteSaamryGatePreview(
        bestuurderId: profile.gebruikerId,
        kampusId: widget.kampusId,
        rigting: profile.voorgesteldeRigting,
      );

      if (!mounted) return;

      final verified = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
          builder: (_) => saamryPreview.hasGroup &&
                  saamryPreview.groepId != null &&
                  saamryPreview.lede.length > 1
              ? WagteSaamryVerifyPage(
                  preview: saamryPreview,
                  kampusId: widget.kampusId,
                  kampusNaam: widget.kampusNaam,
                  metode: metode,
                )
              : WagteVerifyPage(
                  profile: profile,
                  kampusId: widget.kampusId,
                  kampusNaam: widget.kampusNaam,
                  metode: metode,
                ),
        ),
      );

      if (!mounted) return;

      setState(() {
        _status = verified == true
            ? '$metode suksesvol verwerk'
            : 'Gereed – skandeer QR of hou NFC-tag teen die toestel';
      });

      await _resumeAutomaticListening();
    } catch (e) {
      if (!mounted) return;

      final msg = e.toString().replaceFirst('Exception: ', '');

      setState(() {
        _loading = false;
        _status = msg;
      });

      await _resumeAutomaticListening();
    }
  }

  // Sommige skandeerders stuur die hele waarde in een slag;
  // ander stuur karakters vinnig een vir een. Die kort debounce hanteer albei.
  void _handleQrChanged(String value) {
    if (_loading || _manualFocusNode.hasFocus) return;

    final clean = value.trim();
    _qrDebounce?.cancel();

    if (clean.isEmpty) return;

    _qrDebounce = Timer(const Duration(milliseconds: 160), () {
      if (!mounted || _loading || _manualFocusNode.hasFocus) return;

      final latest = _scannerController.text.trim();
      if (latest.isNotEmpty) {
        _submitScan(
          nommer: latest,
          metode: 'QR',
        );
      }
    });
  }

  void _handleQrSubmitted(String value) {
    _qrDebounce?.cancel();

    final clean = value.trim();
    if (clean.isEmpty || _loading) return;

    _submitScan(
      nommer: clean,
      metode: 'QR',
    );
  }

  void _handleManualChanged(String value) {
    _manualDebounce?.cancel();
    final clean = value.trim();

    if (clean.isEmpty) {
      setState(() {
        _manualChecking = false;
        _manualNommerBestaan = null;
        _manualNommerAktief = true;
        _manualNommerTipe = null;
        _manualNommerNaam = null;
      });
      return;
    }

    setState(() {
      _manualChecking = true;
      _manualNommerBestaan = null;
      _manualNommerTipe = null;
      _manualNommerNaam = null;
    });

    _manualDebounce = Timer(const Duration(milliseconds: 350), () async {
      if (!mounted) return;
      final latest = _manualController.text.trim();
      if (latest.isEmpty || latest != clean) return;

      try {
        final result = await MoonApi.wagteNommerCheck(latest);
        if (!mounted || _manualController.text.trim() != latest) return;

        final bestaan = result['bestaan'] == true;
        final aktief = result['aktief'] != false;
        final tipe = result['tipe']?.toString();
        final naam = '${result['naam'] ?? ''} ${result['van'] ?? ''}'.trim();

        setState(() {
          _manualChecking = false;
          _manualNommerBestaan = bestaan;
          _manualNommerAktief = aktief;
          _manualNommerTipe = tipe;
          _manualNommerNaam = naam.isEmpty ? null : naam;
        });
      } catch (_) {
        if (!mounted || _manualController.text.trim() != latest) return;
        setState(() {
          _manualChecking = false;
          _manualNommerBestaan = null;
          _manualNommerTipe = null;
          _manualNommerNaam = null;
        });
      }
    });
  }

  String get _manualValidationText {
    if (_manualChecking) return 'Kontroleer nommer...';
    if (_manualNommerBestaan == false) return 'Nommer bestaan nie';
    if (_manualNommerBestaan == true && !_manualNommerAktief) {
      return 'Gebruiker bestaan maar is gedeaktiveer';
    }
    if (_manualNommerBestaan == true) {
      final tipe = _manualNommerTipe == 'STUDENT'
          ? 'Studentenommer'
          : _manualNommerTipe == 'PERSONEEL'
              ? 'Personeelnommer'
              : 'ID-nommer';
      return _manualNommerNaam == null
          ? '$tipe gevind'
          : '$tipe gevind · $_manualNommerNaam';
    }
    return '';
  }

  Future<void> _submitManual() async {
    final clean = _manualController.text.trim();

    if (clean.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Tik eers ’n student-, personeel- of ID-nommer in'),
        ),
      );
      _manualFocusNode.requestFocus();
      return;
    }

    if (_manualNommerBestaan == false) {
      setState(() => _status = 'Nommer bestaan nie');
      _manualFocusNode.requestFocus();
      return;
    }

    if (_manualNommerBestaan == true && !_manualNommerAktief) {
      setState(() => _status = 'Gebruiker is gedeaktiveer');
      _manualFocusNode.requestFocus();
      return;
    }

    await _submitScan(
      nommer: clean,
      metode: 'HANDMATIG',
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
                    // Versteekte veld wat die MT90 se QR-skandeerder opvang.
                    SizedBox(
                      height: 1,
                      width: 1,
                      child: TextField(
                        controller: _scannerController,
                        focusNode: _scannerFocusNode,
                        autofocus: true,
                        keyboardType: TextInputType.none,
                        showCursor: false,
                        enableInteractiveSelection: false,
                        style: const TextStyle(
                          color: Colors.transparent,
                          fontSize: 1,
                        ),
                        decoration: const InputDecoration(
                          border: InputBorder.none,
                          isCollapsed: true,
                          contentPadding: EdgeInsets.zero,
                        ),
                        onChanged: _handleQrChanged,
                        onSubmitted: _handleQrSubmitted,
                      ),
                    ),

                    // Die enigste sigbare invoerbalk – vir worst-case handmatige invoer.
                    GlassCard(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 6,
                      ),
                      child: TextField(
                        controller: _manualController,
                        focusNode: _manualFocusNode,
                        enabled: !_loading,
                        keyboardType: TextInputType.text,
                        textInputAction: TextInputAction.search,
                        autocorrect: false,
                        enableSuggestions: false,
                        style: GoogleFonts.inter(color: kText1),
                        decoration: InputDecoration(
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(
                              color: _manualChecking
                                  ? Colors.orange
                                  : _manualNommerBestaan == false
                                      ? Colors.red
                                      : _manualNommerBestaan == true
                                          ? (_manualNommerAktief ? Colors.green : Colors.red)
                                          : Colors.transparent,
                              width: 1.6,
                            ),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(
                              color: _manualChecking
                                  ? Colors.orange
                                  : _manualNommerBestaan == false
                                      ? Colors.red
                                      : _manualNommerBestaan == true
                                          ? (_manualNommerAktief ? Colors.green : Colors.red)
                                          : Colors.transparent,
                              width: 1.6,
                            ),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(
                              color: _manualChecking
                                  ? Colors.orange
                                  : _manualNommerBestaan == false
                                      ? Colors.red
                                      : _manualNommerBestaan == true
                                          ? (_manualNommerAktief ? Colors.green : Colors.red)
                                          : kAccent,
                              width: 1.8,
                            ),
                          ),
                          hintText: 'Tik student-, personeel- of ID-nommer...',
                          hintStyle: GoogleFonts.inter(color: kTextMuted, fontSize: 12),
                          helperText: _manualController.text.trim().isEmpty
                              ? null
                              : _manualValidationText,
                          helperStyle: GoogleFonts.inter(
                            color: _manualChecking
                                ? Colors.orange
                                : _manualNommerBestaan == false
                                    ? Colors.red
                                    : _manualNommerBestaan == true
                                        ? (_manualNommerAktief ? Colors.green : Colors.red)
                                        : kTextMuted,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                          ),
                          prefixIcon: Icon(
                            _manualNommerBestaan == false
                                ? Icons.error_outline_rounded
                                : _manualNommerBestaan == true
                                    ? (_manualNommerAktief
                                        ? Icons.check_circle_outline_rounded
                                        : Icons.block_rounded)
                                    : Icons.keyboard_alt_outlined,
                            color: _manualChecking
                                ? Colors.orange
                                : _manualNommerBestaan == false
                                    ? Colors.red
                                    : _manualNommerBestaan == true
                                        ? (_manualNommerAktief ? Colors.green : Colors.red)
                                        : kTextMuted,
                          ),
                          suffixIcon: _manualChecking
                              ? const Padding(
                                  padding: EdgeInsets.all(14),
                                  child: SizedBox(
                                    width: 18,
                                    height: 18,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  ),
                                )
                              : IconButton(
                                  tooltip: 'Soek profiel',
                                  onPressed: _loading ? null : _submitManual,
                                  icon: const Icon(
                                    Icons.search_rounded,
                                    color: kAccent,
                                  ),
                                ),
                        ),
                        onChanged: _handleManualChanged,
                        onTap: () {
                          _scannerFocusNode.unfocus();
                        },
                        onSubmitted: (_) => _submitManual(),
                      ),
                    ),

                    const SizedBox(height: 16),

                    GlassCard(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        children: [
                          const Icon(
                            Icons.document_scanner_outlined,
                            color: kAccent,
                            size: 58,
                          ),
                          const SizedBox(height: 14),
                          Text(
                            _loading ? 'Besig...' : _status,
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            _nfcAvailable
                                ? 'QR en NFC word outomaties opgetel'
                                : 'QR word outomaties opgetel',
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: kTextMuted,
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 16),
                          Wrap(
                            alignment: WrapAlignment.center,
                            spacing: 10,
                            runSpacing: 10,
                            children: [
                              _AutoScanBadge(
                                icon: Icons.qr_code_scanner_rounded,
                                label: 'QR GEREED',
                                active: !_loading,
                              ),
                              _AutoScanBadge(
                                icon: Icons.nfc_rounded,
                                label: _nfcAvailable
                                    ? 'NFC GEREED'
                                    : 'NFC AF',
                                active: _nfcAvailable && !_loading,
                              ),
                            ],
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

class _AutoScanBadge extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool active;

  const _AutoScanBadge({
    required this.icon,
    required this.label,
    required this.active,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: active ? Colors.green.withOpacity(0.12) : Colors.white10,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: active ? Colors.green.withOpacity(0.45) : Colors.white24,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 16,
            color: active ? Colors.green : kTextMuted,
          ),
          const SizedBox(width: 7),
          Text(
            label,
            style: GoogleFonts.inter(
              color: active ? Colors.green : kTextMuted,
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}

class WagteSaamryVerifyPage extends StatefulWidget {
  final SaamryGatePreviewDto preview;
  final int kampusId;
  final String kampusNaam;
  final String metode;

  const WagteSaamryVerifyPage({
    super.key,
    required this.preview,
    required this.kampusId,
    required this.kampusNaam,
    required this.metode,
  });

  @override
  State<WagteSaamryVerifyPage> createState() =>
      _WagteSaamryVerifyPageState();
}

class _WagteSaamryVerifyPageState extends State<WagteSaamryVerifyPage> {
  late String _rigting;
  final Set<int> _selectedIds = <int>{};
  bool _loading = false;
  bool _verified = false;
  int _processedCount = 0;
  int _skippedCount = 0;

  @override
  void initState() {
    super.initState();
    _rigting = widget.preview.rigting;
    _applyDirectionDefaults();
  }

  SaamryGateMemberDto get _driver => widget.preview.lede.firstWhere(
        (member) => member.isBestuurder,
        orElse: () => widget.preview.lede.first,
      );

  void _applyDirectionDefaults() {
    _selectedIds
      ..clear()
      ..add(_driver.gebruikerId);

    for (final member in widget.preview.lede) {
      if (member.isBestuurder) continue;

      final shouldSelect = _rigting == 'IN'
          ? !member.opKampus
          : member.opKampus;

      if (shouldSelect) {
        _selectedIds.add(member.gebruikerId);
      }
    }
  }

  void _toggleRigting() {
    if (_loading || _verified) return;
    setState(() {
      _rigting = _rigting == 'IN' ? 'UIT' : 'IN';
      _applyDirectionDefaults();
    });
  }

  void _toggleMember(SaamryGateMemberDto member, bool? checked) {
    if (_loading || _verified || member.isBestuurder) return;

    setState(() {
      if (checked == true) {
        _selectedIds.add(member.gebruikerId);
      } else {
        _selectedIds.remove(member.gebruikerId);
      }
    });
  }

  String _photoUrl(String raw) {
    if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
    return '${MoonApi.baseUrl}$raw';
  }

  void _showLargePhoto(SaamryGateMemberDto member) {
    final raw = member.fotoUrl?.trim() ?? '';

    showDialog<void>(
      context: context,
      builder: (dialogContext) => Dialog(
        backgroundColor: const Color(0xFF111827),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                member.volleNaam,
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                  color: kText1,
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 14),
              if (raw.isNotEmpty)
                ClipRRect(
                  borderRadius: BorderRadius.circular(18),
                  child: Image.network(
                    _photoUrl(raw),
                    width: 280,
                    height: 280,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const SizedBox(
                      width: 220,
                      height: 220,
                      child: Icon(
                        Icons.person,
                        size: 150,
                        color: kTextMuted,
                      ),
                    ),
                  ),
                )
              else
                const SizedBox(
                  width: 220,
                  height: 220,
                  child: Icon(
                    Icons.person,
                    size: 150,
                    color: kTextMuted,
                  ),
                ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: const Text('Maak Toe'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _confirmGroup() async {
    if (_loading || _verified) return;

    if (_selectedIds.isEmpty || !_selectedIds.contains(_driver.gebruikerId)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Die bestuurder moet gekies wees')),
      );
      return;
    }

    setState(() => _loading = true);

    try {
      final result = await MoonApi.wagteSaamryGateConfirm(
        groepId: widget.preview.groepId!,
        kampusId: widget.kampusId,
        rigting: _rigting,
        metode: widget.metode,
        gebruikerIds: _selectedIds.toList(),
      );

      if (!mounted) return;

      setState(() {
        _processedCount = (result['verwerk_count'] as num?)?.toInt() ?? 0;
        _skippedCount = (result['oorgeslaan_count'] as num?)?.toInt() ?? 0;
        _loading = false;
        _verified = true;
      });

      Future.delayed(const Duration(seconds: 3), () {
        if (!mounted) return;
        Navigator.pop(context, true);
      });
    } catch (e) {
      if (!mounted) return;

      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(
            e.toString().replaceFirst('Exception: ', ''),
          ),
        ),
      );
    }
  }

  Future<void> _denyGroup() async {
    if (_loading || _verified) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: const Color(0xFF111827),
        title: const Text(
          'Weier Voertuigtoegang',
          style: TextStyle(color: Colors.white),
        ),
        content: const Text(
          'Geen persoon in hierdie Saamrygroep sal geskandeer word nie. Gaan voort?',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Kanselleer'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text(
              'Weier',
              style: TextStyle(color: Colors.red),
            ),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      Navigator.pop(context, false);
    }
  }

  Widget _avatar(SaamryGateMemberDto member) {
    final raw = member.fotoUrl?.trim() ?? '';

    return GestureDetector(
      onTap: () => _showLargePhoto(member),
      child: Container(
        width: 72,
        height: 72,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: member.isBestuurder ? kAccent : Colors.white24,
            width: member.isBestuurder ? 2 : 1,
          ),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(14),
          child: raw.isNotEmpty
              ? Image.network(
                  _photoUrl(raw),
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const Icon(
                    Icons.person,
                    color: kTextMuted,
                    size: 52,
                  ),
                )
              : const Icon(
                  Icons.person,
                  color: kTextMuted,
                  size: 52,
                ),
        ),
      ),
    );
  }

  Widget _memberCard(SaamryGateMemberDto member) {
    final selected = _selectedIds.contains(member.gebruikerId);
    final statusText = member.opKampus ? 'OP KAMPUS' : 'NIE OP KAMPUS';
    final statusIcon = member.opKampus
        ? Icons.location_on_rounded
        : Icons.location_off_rounded;
    final statusColor = member.opKampus ? Colors.green : Colors.orange;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Semantics(
        button: true,
        selected: selected,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: _loading || _verified
              ? null
              : () {
                  if (member.isBestuurder) {
                    _showLargePhoto(member);
                  } else {
                    _toggleMember(member, !selected);
                  }
                },
          child: GlassCard(
            padding: const EdgeInsets.all(12),
            child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            _avatar(member),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          member.volleNaam,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.inter(
                            color: kText1,
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      if (member.isBestuurder)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 7,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: kAccent.withOpacity(0.14),
                            borderRadius: BorderRadius.circular(999),
                            border: Border.all(
                              color: kAccent.withOpacity(0.5),
                            ),
                          ),
                          child: Text(
                            'BESTUURDER',
                            style: GoogleFonts.inter(
                              color: kAccent,
                              fontSize: 8,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.4,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 5),
                  Text(
                    '${member.rol} · ${member.nommer}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.inter(
                      color: kText2,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 7),
                  Row(
                    children: [
                      Icon(statusIcon, color: statusColor, size: 16),
                      const SizedBox(width: 5),
                      Text(
                        statusText,
                        style: GoogleFonts.inter(
                          color: statusColor,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 6),
              IgnorePointer(
                child: Checkbox(
                  value: selected,
                  onChanged: member.isBestuurder ? null : (_) {},
                  activeColor: kAccent,
                  checkColor: Colors.black,
                ),
              ),
            ],
          ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final selectedCount = _selectedIds.length;
    final directionWord = _rigting == 'IN' ? 'IN' : 'UIT';

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Saamry Voertuig',
              subtitle: widget.kampusNaam,
              showBack: true,
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                children: [
                  GlassCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(
                              Icons.directions_car_filled_rounded,
                              color: kAccent,
                              size: 30,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                widget.preview.groepNaam ?? 'Saamrygroep',
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: GoogleFonts.inter(
                                  color: kText1,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            Expanded(
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 12,
                                  vertical: 11,
                                ),
                                decoration: BoxDecoration(
                                  color: _rigting == 'IN'
                                      ? Colors.green.withOpacity(0.13)
                                      : Colors.red.withOpacity(0.13),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                    color: _rigting == 'IN'
                                        ? Colors.green
                                        : Colors.red,
                                  ),
                                ),
                                child: Text(
                                  _rigting == 'IN'
                                      ? 'INGANG — PERSONE KOM IN'
                                      : 'UITGANG — PERSONE GAAN UIT',
                                  textAlign: TextAlign.center,
                                  style: GoogleFonts.inter(
                                    color: _rigting == 'IN'
                                        ? Colors.green
                                        : Colors.red,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            IconButton(
                              tooltip: 'Verander rigting',
                              onPressed: _toggleRigting,
                              icon: const Icon(
                                Icons.sync_rounded,
                                color: kAccent,
                                size: 30,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          'Ontmerk enige persoon wat nie in die voertuig is nie. Tik op ’n foto om dit groter te sien.',
                          style: GoogleFonts.inter(
                            color: kTextMuted,
                            fontSize: 11,
                            height: 1.4,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'PERSONE IN DIE VOERTUIG',
                    style: GoogleFonts.inter(
                      color: kTextMuted,
                      fontSize: 9,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1.1,
                    ),
                  ),
                  const SizedBox(height: 10),
                  ...widget.preview.lede.map(_memberCard),
                  const SizedBox(height: 8),
                  if (_verified)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: Colors.green.withOpacity(0.14),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: Colors.green),
                      ),
                      child: Column(
                        children: [
                          const Icon(
                            Icons.verified_rounded,
                            color: Colors.green,
                            size: 52,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '$_processedCount PERSONE $directionWord BEVESTIG',
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: Colors.green,
                              fontSize: 18,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          if (_skippedCount > 0) ...[
                            const SizedBox(height: 6),
                            Text(
                              '$_skippedCount reeds in die korrekte kampusstatus en is nie weer gelog nie.',
                              textAlign: TextAlign.center,
                              style: GoogleFonts.inter(
                                color: kText2,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ],
                      ),
                    )
                  else ...[
                    GradientActionButton(
                      label: _loading
                          ? 'BEVESTIG...'
                          : 'BEVESTIG $selectedCount PERSONE $directionWord',
                      onTap: _confirmGroup,
                      height: 56,
                    ),
                    const SizedBox(height: 10),
                    OutlineActionButton(
                      label: _loading ? 'BESIG...' : 'WEIER VOERTUIGTOEGANG',
                      onTap: _denyGroup,
                      height: 52,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class WagteVerifyPage extends StatefulWidget {
  final WagteProfileScanDto profile;
  final int kampusId;
  final String kampusNaam;
  final String metode;

  const WagteVerifyPage({
    super.key,
    required this.profile,
    required this.kampusId,
    required this.kampusNaam,
    required this.metode,
  });

  @override
  State<WagteVerifyPage> createState() => _WagteVerifyPageState();
}

class _WagteVerifyPageState extends State<WagteVerifyPage> {
  late String _rigting;
  bool _loading = false;
  bool _verified = false;
  bool _declined = false;

  @override
  void initState() {
    super.initState();
    _rigting = widget.profile.voorgesteldeRigting;
  }

  void _toggleRigting() {
    setState(() {
      _rigting = _rigting == 'IN' ? 'UIT' : 'IN';
    });
  }

  Future<void> _verify() async {
    if (_loading) return;

    setState(() => _loading = true);

    try {
      await MoonApi.wagteProfileVerify(
        gebruikerId: widget.profile.gebruikerId,
        kampusId: widget.kampusId,
        rigting: _rigting,
        metode: widget.metode,
      );

      if (!mounted) return;

      setState(() {
        _verified = true;
        _loading = false;
      });

      Future.delayed(const Duration(seconds: 2), () {
        if (!mounted) return;
        Navigator.pop(context, true);
      });
    } catch (e) {
      if (!mounted) return;

      setState(() => _loading = false);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Verify fout: $e')),
      );
    }
  }

  Future<void> _declineAccess() async {
    if (_loading) return;

    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          backgroundColor: const Color(0xFF111827),
          title: const Text(
            'Weier Toegang',
            style: TextStyle(color: Colors.white),
          ),
          content: const Text(
            'Is jy seker jy wil hierdie persoon se toegang weier?',
            style: TextStyle(color: Colors.white70),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Kanselleer'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text(
                'Weier',
                style: TextStyle(color: Colors.red),
              ),
            ),
          ],
        );
      },
    );

    if (confirm != true) return;

    setState(() => _loading = true);

    try {
      await MoonApi.wagteProfileDecline(
        gebruikerId: widget.profile.gebruikerId,
        kampusId: widget.kampusId,
        metode: widget.metode,
      );

      if (!mounted) return;

      setState(() {
        _declined = true;
        _loading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Colors.red,
          content: Text(
            'Toegang geweier',
            style: TextStyle(color: Colors.white),
          ),
        ),
      );

      Future.delayed(const Duration(seconds: 2), () {
        if (!mounted) return;
        Navigator.pop(context, true);
      });
    } catch (e) {
      if (!mounted) return;

      setState(() => _loading = false);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text('Weier fout: $e'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isIn = _rigting == 'IN';

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Bevestig Toegang',
              subtitle: widget.kampusNaam,
              showBack: true,
            ),
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(18),
                  child: GlassCard(
                    padding: const EdgeInsets.all(22),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        if ((widget.profile.fotoUrl ?? '').isNotEmpty)
                          ClipRRect(
                            borderRadius: BorderRadius.circular(60),
                            child: Image.network(
                              '${MoonApi.baseUrl}${widget.profile.fotoUrl}',
                              width: 110,
                              height: 110,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => const Icon(
                                Icons.person,
                                size: 100,
                                color: kTextMuted,
                              ),
                            ),
                          )
                        else
                          const Icon(
                            Icons.person,
                            size: 100,
                            color: kTextMuted,
                          ),

                        const SizedBox(height: 18),

                        Text(
                          '${widget.profile.naam} ${widget.profile.van}',
                          textAlign: TextAlign.center,
                          style: GoogleFonts.inter(
                            color: kText1,
                            fontSize: 24,
                            fontWeight: FontWeight.w800,
                          ),
                        ),

                        const SizedBox(height: 8),

                        Text(
                          widget.profile.idNommer,
                          textAlign: TextAlign.center,
                          style: GoogleFonts.inter(
                            color: kText2,
                            fontSize: 16,
                          ),
                        ),

                        const SizedBox(height: 24),

                        if (_verified)
                          Text(
                            '✔ TOEGANG BEVESTIG',
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: Colors.green,
                              fontSize: 22,
                              fontWeight: FontWeight.w900,
                            ),
                          )
                        else if (_declined)
                          Text(
                            '✖ TOEGANG GEWEIER',
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: Colors.red,
                              fontSize: 22,
                              fontWeight: FontWeight.w900,
                            ),
                          )
                        else ...[
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                isIn ? '🟢 IN' : '🔴 UIT',
                                style: GoogleFonts.inter(
                                  color: isIn ? Colors.green : Colors.red,
                                  fontSize: 22,
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                              const SizedBox(width: 16),
                              InkWell(
                                onTap: _toggleRigting,
                                borderRadius: BorderRadius.circular(30),
                                child: const Padding(
                                  padding: EdgeInsets.all(10),
                                  child: Icon(
                                    Icons.sync_rounded,
                                    color: kAccent,
                                    size: 30,
                                  ),
                                ),
                              ),
                            ],
                          ),

                          const SizedBox(height: 24),

                          Row(
                            children: [
                              Expanded(
                                child: GradientActionButton(
                                  label: _loading ? 'BEVESTIG...' : 'BEVESTIG',
                                  onTap: _verify,
                                  height: 54,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: OutlineActionButton(
                                  label: _loading ? 'BESIG...' : 'WEIER',
                                  onTap: _declineAccess,
                                  height: 54,
                                ),
                              ),
                            ],
                          ),
                        ],
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

class OnverwagteBesoekerPage extends StatefulWidget {
  const OnverwagteBesoekerPage({super.key});

  @override
  State<OnverwagteBesoekerPage> createState() => _OnverwagteBesoekerPageState();
}

class _OnverwagteBesoekerPageState extends State<OnverwagteBesoekerPage> {
  final TextEditingController _redeController = TextEditingController();
  final ImagePicker _picker = ImagePicker();

  XFile? _lisensieFoto;

  @override
  void dispose() {
    _redeController.dispose();
    super.dispose();
  }

  Future<void> _neemFoto() async {
    final foto = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 70,
    );

    if (foto == null) return;

    setState(() {
      _lisensieFoto = foto;
    });
  }

  void _registreer() {
    if (_lisensieFoto == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Neem eers ’n foto van die bestuurslisensie')),
      );
      return;
    }

    if (_redeController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vul asseblief die rede vir besoek in')),
      );
      return;
    }

    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Besoeker geregistreer'),
        content: const Text('Onverwagte besoeker is voorlopig geregistreer.'),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              setState(() {
                _lisensieFoto = null;
                _redeController.clear();
              });
            },
            child: const Text('OK'),
          ),
        ],
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
              title: 'Onverwagte Besoeker',
              subtitle: 'Lisensie foto en rede',
              showBack: true,
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    GlassCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'BESTUURSLISENSIE',
                            style: GoogleFonts.inter(
                              color: kTextMuted,
                              fontSize: 9,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1.1,
                            ),
                          ),
                          const SizedBox(height: 12),
                          GestureDetector(
                            onTap: _neemFoto,
                            child: Container(
                              height: 210,
                              width: double.infinity,
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(18),
                                border: Border.all(color: Colors.white24),
                                color: Colors.white10,
                              ),
                              child: _lisensieFoto == null
                                  ? Center(
                                      child: Text(
                                        '📷 Neem foto van bestuurslisensie',
                                        textAlign: TextAlign.center,
                                        style: GoogleFonts.inter(
                                          color: kText1,
                                          fontWeight: FontWeight.w700,
                                        ),
                                      ),
                                    )
                                  : ClipRRect(
                                      borderRadius: BorderRadius.circular(18),
                                      child: Image.file(
                                        File(_lisensieFoto!.path),
                                        fit: BoxFit.cover,
                                      ),
                                    ),
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 16),

                    GlassCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'REDE VIR BESOEK',
                            style: GoogleFonts.inter(
                              color: kTextMuted,
                              fontSize: 9,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1.1,
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: _redeController,
                            maxLines: 4,
                            style: GoogleFonts.inter(color: kText1),
                            decoration: InputDecoration(
                              hintText: 'Byvoorbeeld: vergadering, aflewering, onderhoud...',
                              hintStyle: GoogleFonts.inter(color: kTextMuted),
                              filled: true,
                              fillColor: Colors.white10,
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(16),
                                borderSide: const BorderSide(color: Colors.white24),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(16),
                                borderSide: const BorderSide(color: Colors.white24),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(16),
                                borderSide: const BorderSide(color: kAccent),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 22),

                    GradientActionButton(
                      label: 'Registreer Besoeker',
                      onTap: _registreer,
                      height: 54,
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
  final int kampusId;
  final String kampusNaam;

  const VisitorVerifyPage({
    super.key,
    required this.kampusId,
    required this.kampusNaam,
  });

  @override
  State<VisitorVerifyPage> createState() => _VisitorVerifyPageState();
}

class _VisitorVerifyPageState extends State<VisitorVerifyPage> {
  final TextEditingController _otpController = TextEditingController();

  bool _loading = false;
  bool _decisionLoading = false;
  BesoekerUitnodigingDto? _invite;
  String? _error;

  @override
  void dispose() {
    _otpController.dispose();
    super.dispose();
  }

  String _formatDateTime(DateTime value) {
    final day = value.day.toString().padLeft(2, '0');
    final month = value.month.toString().padLeft(2, '0');
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');
    return '$day/$month/${value.year} $hour:$minute';
  }

  Future<void> _verifyOtp() async {
    if (_loading || _decisionLoading) return;

    final otp = _otpController.text.trim();

    if (otp.length != 6 || int.tryParse(otp) == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('OTP moet presies 6 syfers wees')),
      );
      return;
    }

    FocusScope.of(context).unfocus();

    setState(() {
      _loading = true;
      _invite = null;
      _error = null;
    });

    try {
      final invite = await MoonApi.verifyVisitorOtp(otp);

      if (!mounted) return;

      setState(() {
        _loading = false;
        _invite = invite;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _loading = false;
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<bool> _confirmDecision({
    required String title,
    required String message,
    required String action,
    required Color actionColor,
  }) async {
    return await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            backgroundColor: const Color(0xFF111827),
            title: Text(
              title,
              style: const TextStyle(color: Colors.white),
            ),
            content: Text(
              message,
              style: const TextStyle(color: Colors.white70),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('Kanselleer'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: Text(
                  action,
                  style: TextStyle(color: actionColor),
                ),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _allowEntry() async {
    final invite = _invite;
    if (invite == null || _decisionLoading) return;

    final confirmed = await _confirmDecision(
      title: 'Laat Toegang Toe',
      message:
          'Laat ${invite.volleNaam} toegang toe by ${widget.kampusNaam}?',
      action: 'Laat Toe',
      actionColor: Colors.green,
    );
    if (!confirmed) return;

    setState(() => _decisionLoading = true);

    try {
      final updated = await MoonApi.allowVisitorEntry(
        uitnodigingId: invite.uitnodigingId,
        kampusId: widget.kampusId,
      );

      if (!mounted) return;

      setState(() {
        _decisionLoading = false;
        _invite = updated;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Colors.green,
          content: Text('Besoekertoegang toegestaan'),
        ),
      );
    } catch (e) {
      if (!mounted) return;

      setState(() => _decisionLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    }
  }

  Future<void> _denyEntry() async {
    final invite = _invite;
    if (invite == null || _decisionLoading) return;

    final confirmed = await _confirmDecision(
      title: 'Weier Toegang',
      message:
          'Weier ${invite.volleNaam} se toegang by ${widget.kampusNaam}?',
      action: 'Weier',
      actionColor: Colors.red,
    );
    if (!confirmed) return;

    setState(() => _decisionLoading = true);

    try {
      final updated = await MoonApi.denyVisitorEntry(
        uitnodigingId: invite.uitnodigingId,
        kampusId: widget.kampusId,
      );

      if (!mounted) return;

      setState(() {
        _decisionLoading = false;
        _invite = updated;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Colors.red,
          content: Text('Besoekertoegang geweier'),
        ),
      );
    } catch (e) {
      if (!mounted) return;

      setState(() => _decisionLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    }
  }

  void _nextVisitor() {
    setState(() {
      _invite = null;
      _error = null;
      _otpController.clear();
    });
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'TOEGELAAT':
        return Colors.green;
      case 'GEWEIER':
        return Colors.red;
      case 'VERVAL':
      case 'GEKANSELLEER':
        return kTextMuted;
      default:
        return Colors.orange;
    }
  }

  @override
  Widget build(BuildContext context) {
    final invite = _invite;
    final pending = invite?.status == 'HANGEND';

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Besoeker OTP',
              subtitle: widget.kampusNaam,
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
                            'VERIFIEER OTP',
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
                            hintText: 'Tik 6-syfer besoeker OTP',
                            keyboardType: TextInputType.number,
                            prefixIcon: const Icon(
                              Icons.password_rounded,
                              color: kTextMuted,
                              size: 18,
                            ),
                          ),
                          const SizedBox(height: 16),
                          GradientActionButton(
                            label: _loading ? 'VERIFIEER...' : 'VERIFIEER OTP',
                            onTap: _loading ? () {} : _verifyOtp,
                            height: 50,
                          ),
                        ],
                      ),
                    ),

                    if (_error != null) ...[
                      const SizedBox(height: 16),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.red.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.red.withOpacity(0.6)),
                        ),
                        child: Column(
                          children: [
                            const Icon(
                              Icons.error_outline_rounded,
                              color: Colors.red,
                              size: 42,
                            ),
                            const SizedBox(height: 10),
                            Text(
                              _error!,
                              textAlign: TextAlign.center,
                              style: GoogleFonts.inter(
                                color: Colors.red,
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],

                    if (invite != null) ...[
                      const SizedBox(height: 18),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(18),
                        decoration: BoxDecoration(
                          color: _statusColor(invite.status).withOpacity(0.12),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: _statusColor(invite.status),
                            width: 1.5,
                          ),
                        ),
                        child: Column(
                          children: [
                            Icon(
                              pending
                                  ? Icons.verified_user_outlined
                                  : invite.status == 'TOEGELAAT'
                                      ? Icons.check_circle_rounded
                                      : Icons.cancel_rounded,
                              color: _statusColor(invite.status),
                              size: 58,
                            ),
                            const SizedBox(height: 12),
                            Text(
                              pending
                                  ? 'GELDIGE BESOEKER'
                                  : invite.status,
                              style: GoogleFonts.inter(
                                color: _statusColor(invite.status),
                                fontSize: 13,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 1.1,
                              ),
                            ),
                            const SizedBox(height: 16),
                            Text(
                              invite.volleNaam,
                              textAlign: TextAlign.center,
                              style: GoogleFonts.inter(
                                color: kText1,
                                fontSize: 22,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Genooi deur ${invite.gasheerNaam}',
                              textAlign: TextAlign.center,
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
                                    label: 'Selfoon',
                                    value: invite.selfoon,
                                  ),
                                  const _VisitorDivider(),
                                  _VisitorInfoRow(
                                    label: 'Rede',
                                    value: invite.rede,
                                  ),
                                  const _VisitorDivider(),
                                  _VisitorInfoRow(
                                    label: 'OTP',
                                    value: invite.otp,
                                  ),
                                  const _VisitorDivider(),
                                  _VisitorInfoRow(
                                    label: 'Verval',
                                    value: _formatDateTime(invite.vervalOp),
                                  ),
                                  const _VisitorDivider(),
                                  _VisitorInfoRow(
                                    label: 'Status',
                                    value: invite.status,
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 18),
                            if (pending)
                              Wrap(
                                alignment: WrapAlignment.center,
                                spacing: 12,
                                runSpacing: 12,
                                children: [
                                  SizedBox(
                                    width: 150,
                                    child: GradientActionButton(
                                      label: _decisionLoading
                                          ? 'BESIG...'
                                          : 'LAAT TOE',
                                      onTap: _decisionLoading
                                          ? () {}
                                          : _allowEntry,
                                      height: 48,
                                    ),
                                  ),
                                  SizedBox(
                                    width: 150,
                                    child: OutlineActionButton(
                                      label: _decisionLoading
                                          ? 'BESIG...'
                                          : 'WEIER',
                                      onTap: _decisionLoading
                                          ? () {}
                                          : _denyEntry,
                                      height: 48,
                                    ),
                                  ),
                                ],
                              )
                            else
                              OutlineActionButton(
                                label: 'Volgende Besoeker',
                                onTap: _nextVisitor,
                                height: 48,
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