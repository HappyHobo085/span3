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
  SkandeerPlekDto? _gekosePlek;
  List<SkandeerPlekDto> _skandeerPlekke = [];
  bool _plekkeLoading = true;

  @override
  void initState() {
    super.initState();
    _loadSkandeerPlekke();
  }

  Future<void> _loadSkandeerPlekke() async {
    try {
      final plekke = await MoonApi.fetchWagteSkandeerPlekke();

      if (!mounted) return;

      setState(() {
        _skandeerPlekke = plekke;
        _gekosePlek = plekke.isNotEmpty ? plekke.first : null;
        _plekkeLoading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _plekkeLoading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Kon nie skandeerplekke laai nie: $e')),
      );
    }
  }

  void _openScan() {
    final plek = _gekosePlek;

    if (plek == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Kies eers ’n skandeerplek')),
      );
      return;
    }

    if (plek.kampusId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Hierdie skandeerplek het nie ’n geldige kampuskoppeling nie'),
        ),
      );
      return;
    }

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => KampusSkandeerPage(
          kampusId: plek.kampusId!,
          kampusNaam: plek.naam,
          lokasieId: plek.lokasieId,
          koshuisId: plek.koshuisId,
          scanPlekTipe: plek.tipe,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final plek = _gekosePlek;
    final scanLabel =
        plek?.isKoshuis == true ? 'KOSHUISSKANDERING' : 'KAMPUSSKANDERING';

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Wagte',
            ),

            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: GlassCard(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: _plekkeLoading
                    ? const Padding(
                        padding: EdgeInsets.all(14),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    : InkWell(
                        borderRadius: BorderRadius.circular(14),
                        onTap: () async {
                          final selected = await showMenu<SkandeerPlekDto>(
                            context: context,
                            position: const RelativeRect.fromLTRB(16, 130, 16, 0),
                            color: kBg,
                            items: _skandeerPlekke.map((plek) {
                              return PopupMenuItem<SkandeerPlekDto>(
                                value: plek,
                                child: Row(
                                  children: [
                                    Icon(
                                      plek.isKoshuis
                                          ? Icons.apartment_rounded
                                          : Icons.location_on_rounded,
                                      color: kAccent,
                                      size: 19,
                                    ),
                                    const SizedBox(width: 9),
                                    Expanded(
                                      child: Text(
                                        plek.naam,
                                        style: GoogleFonts.inter(color: kText1),
                                      ),
                                    ),
                                    Text(
                                      plek.isKoshuis ? 'KOSHUIS' : 'KAMPUS',
                                      style: GoogleFonts.inter(
                                        color: kTextMuted,
                                        fontSize: 9,
                                        fontWeight: FontWeight.w800,
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            }).toList(),
                          );

                          if (selected != null) {
                            setState(() {
                              _gekosePlek = selected;
                            });
                          }
                        },
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 4,
                            vertical: 15,
                          ),
                          child: Row(
                            children: [
                              Icon(
                                plek?.isKoshuis == true
                                    ? Icons.apartment_rounded
                                    : Icons.location_on_rounded,
                                color: kAccent,
                                size: 22,
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'KIES SKANDEERPLEK',
                                      style: GoogleFonts.inter(
                                        color: kTextMuted,
                                        fontSize: 9,
                                        fontWeight: FontWeight.w800,
                                        letterSpacing: 0.8,
                                      ),
                                    ),
                                    const SizedBox(height: 3),
                                    Text(
                                      plek?.naam ?? 'Kies skandeerplek',
                                      style: GoogleFonts.inter(
                                        color: kText1,
                                        fontSize: 14,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ],
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
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
                child: Column(
                  children: [
                    SizedBox(
                      width: double.infinity,
                      height: 190,
                      child: GlassTapPanel(
                        label: scanLabel,
                        subtitle: 'QR • NFC • Handmatig',
                        icon: plek?.isKoshuis == true ? '🏠' : '🚪',
                        onTap: _openScan,
                      ),
                    ),
                    const SizedBox(height: 14),
                    SizedBox(
                      height: 150,
                      child: Row(
                        children: [
                          Expanded(
                            child: GlassTapPanel(
                              label: 'BESOEKERS',
                              subtitle: 'OTP IN • UIT',
                              icon: '👤',
                              borderColor: const Color(0x3300C2FF),
                              onTap: () {
                                final selected = _gekosePlek;
                                if (selected == null ||
                                    !selected.isKampus ||
                                    selected.kampusId == null) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text(
                                        'Kies ’n kampus as skandeerplek vir besoekers',
                                      ),
                                    ),
                                  );
                                  return;
                                }

                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) => VisitorVerifyPage(
                                      kampusId: selected.kampusId!,
                                      kampusNaam: selected.naam,
                                    ),
                                  ),
                                );
                              },
                            ),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: GlassTapPanel(
                              label: 'ONVERWAGTE\nBESOEKER',
                              subtitle: 'Lisensie & rede',
                              icon: '📷',
                              borderColor: Colors.orangeAccent.withValues(alpha: 0.35),
                              onTap: () {
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) => const OnverwagteBesoekerPage(),
                                  ),
                                );
                              },
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

class KampusSkandeerPage extends StatefulWidget {
  // kampusId bly die administratiewe kampuskoppeling.
  // lokasieId bepaal waar die toegang werklik gelog word.
  final int kampusId;
  final String kampusNaam;
  final int lokasieId;
  final int? koshuisId;
  final String scanPlekTipe;

  const KampusSkandeerPage({
    super.key,
    required this.kampusId,
    required this.kampusNaam,
    required this.lokasieId,
    required this.koshuisId,
    required this.scanPlekTipe,
  });

  bool get isKoshuis => scanPlekTipe.toUpperCase() == 'KOSHUIS';
  bool get isKampus => scanPlekTipe.toUpperCase() == 'KAMPUS';

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
  String _status = 'Gereed – skandeer QR of hou NFC-etiket teen die toestel';

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
              _status = 'NFC-etiket bevat nie ’n leesbare nommer nie';
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
      // Event QR's is net 'n KAMPUS-funksie.
      if (metode == 'QR' &&
          cleanNommer.toUpperCase().startsWith('MOON-EVENT:')) {
        if (!widget.isKampus) {
          throw Exception(
            '’n Geleentheid-QR-kode kan net by ’n kampusskandeerplek gebruik word',
          );
        }

        final preview = await MoonApi.wagteEventGuestPreview(
          scanKode: cleanNommer,
          kampusId: widget.kampusId,
        );

        if (!mounted) return;
        _scannerController.clear();
        setState(() {
          _loading = false;
          _status = 'RSVP van geleentheidsgas gevind';
        });

        final verified = await Navigator.push<bool>(
          context,
          MaterialPageRoute(
            builder: (_) => WagteEventGuestVerifyPage(
              preview: preview,
              kampusId: widget.kampusId,
              kampusNaam: widget.kampusNaam,
            ),
          ),
        );

        if (!mounted) return;
        setState(() {
          _status = verified == true
              ? 'Geleentheidsgas suksesvol verwerk'
              : 'Gereed – skandeer QR of hou NFC-etiket teen die toestel';
        });
        await _resumeAutomaticListening();
        return;
      }

      final profile = await MoonApi.wagteProfileScan(
        cleanNommer,
        lokasieId: widget.lokasieId,
        koshuisId: widget.koshuisId,
      );

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

      Widget verifyPage;

      if (widget.isKoshuis) {
        // Koshuis: geen Saamry/event-vloei nie; slegs die individuele inwoner.
        verifyPage = WagteVerifyPage(
          profile: profile,
          kampusId: widget.kampusId,
          kampusNaam: widget.kampusNaam,
          lokasieId: widget.lokasieId,
          koshuisId: widget.koshuisId,
          scanPlekTipe: widget.scanPlekTipe,
          metode: metode,
        );
      } else {
        final saamryPreview = await MoonApi.wagteSaamryGatePreview(
          bestuurderId: profile.gebruikerId,
          kampusId: widget.kampusId,
          rigting: profile.voorgesteldeRigting,
        );

        if (!mounted) return;

        if (saamryPreview.blockedByEvent) {
          setState(() {
            _loading = false;
            _status = saamryPreview.rede ??
                'Hierdie passasier moet saam met die bestuurder se aktiewe Saamry-rit skandeer';
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              backgroundColor: Colors.orange.shade800,
              content: Text(
                saamryPreview.rede ??
                    'Hierdie passasier is deel van ’n aktiewe Saamry-rit. Skandeer die bestuurder.',
              ),
            ),
          );
          await _resumeAutomaticListening();
          return;
        }

        verifyPage = saamryPreview.hasGroup &&
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
                lokasieId: widget.lokasieId,
                koshuisId: widget.koshuisId,
                scanPlekTipe: widget.scanPlekTipe,
                metode: metode,
              );
      }

      final verified = await Navigator.push<bool>(
        context,
        MaterialPageRoute(builder: (_) => verifyPage),
      );

      if (!mounted) return;

      setState(() {
        _status = verified == true
            ? '$metode suksesvol verwerk'
            : 'Gereed – skandeer QR of hou NFC-etiket teen die toestel';
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
        SnackBar(
          content: Text(
            widget.isKoshuis
                ? 'Tik eers ’n student- of ID-nommer in'
                : 'Tik eers ’n student-, personeel- of ID-nommer in',
          ),
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
              title: widget.isKoshuis ? 'Koshuisskandering' : 'Kampusskandering',
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
                          hintText: widget.isKoshuis
                              ? 'Tik student- of ID-nommer...'
                              : 'Tik student-, personeel- of ID-nommer...',
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
        color: active ? Colors.green.withValues(alpha: 0.12) : Colors.white10,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: active ? Colors.green.withValues(alpha: 0.45) : Colors.white24,
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


class WagteEventGuestVerifyPage extends StatefulWidget {
  final EventGuestGatePreviewDto preview;
  final int kampusId;
  final String kampusNaam;

  const WagteEventGuestVerifyPage({
    super.key,
    required this.preview,
    required this.kampusId,
    required this.kampusNaam,
  });

  @override
  State<WagteEventGuestVerifyPage> createState() =>
      _WagteEventGuestVerifyPageState();
}

class _WagteEventGuestVerifyPageState
    extends State<WagteEventGuestVerifyPage> {
  bool _loading = false;
  bool _verified = false;
  bool _declined = false;

  String _dateTime(DateTime value) {
    final d = value.day.toString().padLeft(2, '0');
    final m = value.month.toString().padLeft(2, '0');
    final h = value.hour.toString().padLeft(2, '0');
    final min = value.minute.toString().padLeft(2, '0');
    return '$d/$m/${value.year} · $h:$min';
  }

  Future<void> _confirm() async {
    if (_loading || _verified || _declined) return;
    setState(() => _loading = true);
    try {
      await MoonApi.wagteEventGuestConfirm(
        publiekRsvpId: widget.preview.publiekRsvpId,
        kampusId: widget.kampusId,
        rigting: widget.preview.voorgesteldeRigting,
        metode: 'QR',
      );
      if (!mounted) return;
      setState(() {
        _verified = true;
        _loading = false;
      });
      Future.delayed(const Duration(milliseconds: 1200), () {
        if (mounted) Navigator.pop(context, true);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    }
  }

  Future<void> _decline() async {
    if (_loading || _verified || _declined) return;
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF111827),
        title: const Text(
          'Weier toegang tot geleentheid',
          style: TextStyle(color: Colors.white),
        ),
        content: Text(
          'Weier toegang vir ${widget.preview.volleNaam}?',
          style: const TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Kanselleer'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('WEIER', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
    if (yes != true) return;

    setState(() => _loading = true);
    try {
      await MoonApi.wagteEventGuestDecline(
        publiekRsvpId: widget.preview.publiekRsvpId,
        kampusId: widget.kampusId,
        metode: 'QR',
      );
      if (!mounted) return;
      setState(() {
        _declined = true;
        _loading = false;
      });
      Future.delayed(const Duration(milliseconds: 1200), () {
        if (mounted) Navigator.pop(context, true);
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.preview;
    final isIn = p.voorgesteldeRigting == 'IN';

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Geleentheidsgas',
              subtitle: widget.kampusNaam,
              showBack: true,
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: Colors.green.withValues(alpha: 0.14),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: Colors.green.withValues(alpha: 0.7),
                          width: 1.3,
                        ),
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.verified_rounded,
                            color: Colors.green,
                            size: 30,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              'GELDIGE RSVP VIR GELEENTHEID',
                              style: GoogleFonts.inter(
                                color: Colors.green,
                                fontSize: 14,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 0.7,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    GlassCard(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        children: [
                          const Icon(
                            Icons.account_circle_rounded,
                            color: kAccent,
                            size: 76,
                          ),
                          const SizedBox(height: 10),
                          Text(
                            p.volleNaam,
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 23,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          const SizedBox(height: 7),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 5,
                            ),
                            decoration: BoxDecoration(
                              color: kAccent.withValues(alpha: 0.13),
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(
                                color: kAccent.withValues(alpha: 0.5),
                              ),
                            ),
                            child: Text(
                              'EKSTERNE GAS',
                              style: GoogleFonts.inter(
                                color: kAccent,
                                fontSize: 9,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 0.8,
                              ),
                            ),
                          ),
                          if ((p.selfoon ?? '').trim().isNotEmpty) ...[
                            const SizedBox(height: 9),
                            Text(
                              p.selfoon!,
                              style: GoogleFonts.inter(
                                color: kText2,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    GlassCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'GELEENTHEID',
                            style: GoogleFonts.inter(
                              color: kTextMuted,
                              fontSize: 9,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 1.0,
                            ),
                          ),
                          const SizedBox(height: 7),
                          Text(
                            p.eventNaam,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 7),
                          Text(
                            p.kampusNaam,
                            style: GoogleFonts.inter(
                              color: kText2,
                              fontSize: 12,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${_dateTime(p.beginTyd)} – ${_dateTime(p.eindTyd)}',
                            style: GoogleFonts.inter(
                              color: kTextMuted,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    Container(
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: isIn
                            ? Colors.green.withValues(alpha: 0.13)
                            : kAccent.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: isIn
                              ? Colors.green.withValues(alpha: 0.65)
                              : kAccent.withValues(alpha: 0.6),
                        ),
                      ),
                      child: Column(
                        children: [
                          Text(
                            'VOORGESTELDE AKSIE',
                            style: GoogleFonts.inter(
                              color: kTextMuted,
                              fontSize: 9,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.9,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            isIn ? '🟢 IN' : '🔵 UIT',
                            style: GoogleFonts.inter(
                              color: isIn ? Colors.green : kAccent,
                              fontSize: 25,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 18),
                    if (_verified)
                      Text(
                        '✔ GELEENTHEIDTOEGANG BEVESTIG',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(
                          color: Colors.green,
                          fontSize: 19,
                          fontWeight: FontWeight.w900,
                        ),
                      )
                    else if (_declined)
                      Text(
                        '✖ GELEENTHEIDTOEGANG GEWEIER',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(
                          color: Colors.red,
                          fontSize: 19,
                          fontWeight: FontWeight.w900,
                        ),
                      )
                    else ...[
                      GradientActionButton(
                        label: _loading
                            ? 'BESIG...'
                            : 'BEVESTIG ${p.voorgesteldeRigting}',
                        onTap: _confirm,
                        height: 56,
                      ),
                      const SizedBox(height: 10),
                      OutlineActionButton(
                        label: 'WEIER TOEGANG',
                        onTap: _loading ? () {} : _decline,
                        height: 52,
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
        eventId: widget.preview.eventId,
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

  Widget _memberGridCard(SaamryGateMemberDto member) {
    final selected = _selectedIds.contains(member.gebruikerId);
    final raw = member.fotoUrl?.trim() ?? '';
    final statusText = member.opKampus ? 'OP KAMPUS' : 'NIE OP KAMPUS';
    final statusColor = member.opKampus ? Colors.green : Colors.orange;
    final selectionColor = selected ? Colors.green : Colors.white24;

    void handleTap() {
      if (_loading || _verified) return;
      if (member.isBestuurder) {
        _showLargePhoto(member);
        return;
      }
      _toggleMember(member, !selected);
    }

    return Semantics(
      button: true,
      selected: selected,
      label: '${member.volleNaam}, ${member.rol}, ${member.nommer}',
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: handleTap,
        onLongPress: () => _showLargePhoto(member),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          decoration: BoxDecoration(
            color: selected
                ? Colors.green.withValues(alpha: 0.08)
                : Colors.white.withValues(alpha: 0.035),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: selectionColor,
              width: selected ? 2 : 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                flex: 7,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    ClipRRect(
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(14),
                      ),
                      child: AnimatedOpacity(
                        duration: const Duration(milliseconds: 160),
                        opacity: selected ? 1.0 : 0.48,
                        child: raw.isNotEmpty
                            ? Image.network(
                                _photoUrl(raw),
                                fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) => Container(
                                  color: Colors.white10,
                                  child: const Icon(
                                    Icons.person,
                                    color: kTextMuted,
                                    size: 82,
                                  ),
                                ),
                              )
                            : Container(
                                color: Colors.white10,
                                child: const Icon(
                                  Icons.person,
                                  color: kTextMuted,
                                  size: 82,
                                ),
                              ),
                      ),
                    ),
                    Positioned(
                      top: 8,
                      right: 8,
                      child: Container(
                        width: 30,
                        height: 30,
                        decoration: BoxDecoration(
                          color: selected
                              ? Colors.green
                              : const Color(0xCC111827),
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: selected ? Colors.green : Colors.white38,
                          ),
                        ),
                        child: Icon(
                          selected
                              ? Icons.check_rounded
                              : Icons.radio_button_unchecked_rounded,
                          color: Colors.white,
                          size: 20,
                        ),
                      ),
                    ),
                    if (member.isBestuurder)
                      Positioned(
                        left: 8,
                        bottom: 8,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 5,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.green.withValues(alpha: 0.92),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: Text(
                            'BESTUURDER',
                            style: GoogleFonts.inter(
                              color: Colors.white,
                              fontSize: 8,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 0.4,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              Expanded(
                flex: 4,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(10, 9, 10, 10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        member.volleNaam,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.inter(
                          color: selected ? kText1 : kText2,
                          fontSize: 13,
                          fontWeight: FontWeight.w800,
                          height: 1.15,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${member.rol} · ${member.nommer}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.inter(
                          color: kTextMuted,
                          fontSize: 9.5,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const Spacer(),
                      Row(
                        children: [
                          Icon(
                            member.opKampus
                                ? Icons.location_on_rounded
                                : Icons.location_off_rounded,
                            color: statusColor,
                            size: 14,
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              statusText,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: GoogleFonts.inter(
                                color: statusColor,
                                fontSize: 8.5,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
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
              title: 'Saamryvoertuig',
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
                                      ? Colors.green.withValues(alpha: 0.13)
                                      : Colors.red.withValues(alpha: 0.13),
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
                          'Tik op ’n kaart om ’n passasier te kies of ontkies. Die bestuurder bly altyd gekies. Hou ’n kaart in vir ’n groter foto.',
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
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: widget.preview.lede.length,
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 12,
                      mainAxisSpacing: 12,
                      childAspectRatio: 0.64,
                    ),
                    itemBuilder: (context, index) {
                      return _memberGridCard(widget.preview.lede[index]);
                    },
                  ),
                  const SizedBox(height: 16),
                  if (_verified)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: Colors.green.withValues(alpha: 0.14),
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
                              '$_skippedCount reeds in die korrekte kampusstatus en is nie weer aangeteken nie.',
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
  final int lokasieId;
  final int? koshuisId;
  final String scanPlekTipe;
  final String metode;

  const WagteVerifyPage({
    super.key,
    required this.profile,
    required this.kampusId,
    required this.kampusNaam,
    required this.lokasieId,
    required this.koshuisId,
    required this.scanPlekTipe,
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
        lokasieId: widget.lokasieId,
        koshuisId: widget.koshuisId,
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
        SnackBar(content: Text('Verifikasiefout: $e')),
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
        lokasieId: widget.lokasieId,
        koshuisId: widget.koshuisId,
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
          content: Text('Weierfout: $e'),
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
              subtitle: 'Lisensiefoto en rede',
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
      title: 'Skandeer Besoeker IN',
      message:
          'Skandeer ${invite.volleNaam} IN by ${widget.kampusNaam}?',
      action: 'SKANDEER IN',
      actionColor: Colors.green,
    );
    if (!confirmed) return;

    setState(() => _decisionLoading = true);

    try {
      await MoonApi.allowVisitorEntry(
        uitnodigingId: invite.uitnodigingId,
        kampusId: widget.kampusId,
      );

      if (!mounted) return;

      setState(() {
        _decisionLoading = false;
        _invite = null;
        _error = null;
        _otpController.clear();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Colors.green,
          content: Text(
            'Besoeker IN geskandeer. Gebruik dieselfde OTP om later UIT te skandeer.',
          ),
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

  Future<void> _exitVisitor() async {
    final invite = _invite;
    if (invite == null || _decisionLoading) return;

    final confirmed = await _confirmDecision(
      title: 'Skandeer Besoeker UIT',
      message:
          'Skandeer ${invite.volleNaam} UIT by ${widget.kampusNaam}? Daarna kan hierdie OTP nie weer gebruik word nie.',
      action: 'SKANDEER UIT',
      actionColor: Colors.orangeAccent,
    );
    if (!confirmed) return;

    setState(() => _decisionLoading = true);

    try {
      await MoonApi.exitVisitor(
        uitnodigingId: invite.uitnodigingId,
        kampusId: widget.kampusId,
      );

      if (!mounted) return;

      setState(() {
        _decisionLoading = false;
        _invite = null;
        _error = null;
        _otpController.clear();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Colors.orange,
          content: Text(
            'Besoeker UIT geskandeer. Hierdie OTP is nou klaar gebruik.',
          ),
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
      case 'UIT':
        return Colors.orangeAccent;
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
    final checkedIn = invite?.status == 'TOEGELAAT';
    final checkedOut = invite?.status == 'UIT';

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
                            hintText: 'Tik die 6-syfer-besoeker-OTP',
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
                          color: Colors.red.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.red.withValues(alpha: 0.6)),
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
                          color: _statusColor(invite.status).withValues(alpha: 0.12),
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
                                  : checkedIn
                                      ? Icons.login_rounded
                                      : checkedOut
                                          ? Icons.logout_rounded
                                          : Icons.cancel_rounded,
                              color: _statusColor(invite.status),
                              size: 58,
                            ),
                            const SizedBox(height: 12),
                            Text(
                              pending
                                  ? 'GELDIGE OTP — SKANDEER IN'
                                  : checkedIn
                                      ? 'BESOEKER IS IN — SKANDEER UIT'
                                      : checkedOut
                                          ? 'BESOEKER UIT'
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
                                          : 'SKANDEER IN',
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
                            else if (checkedIn)
                              SizedBox(
                                width: double.infinity,
                                child: GradientActionButton(
                                  label: _decisionLoading
                                      ? 'BESIG...'
                                      : 'SKANDEER UIT',
                                  onTap: _decisionLoading
                                      ? () {}
                                      : _exitVisitor,
                                  height: 48,
                                ),
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