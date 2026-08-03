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
        _manualController.clear();
      }

      setState(() {
        _loading = false;
        _status = 'Profiel gevind via $metode';
      });

      final verified = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
          builder: (_) => WagteVerifyPage(
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
                        horizontal: 12,
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
                          border: InputBorder.none,
                          hintText: 'Tik nommer handmatig...',
                          hintStyle: GoogleFonts.inter(color: kTextMuted),
                          prefixIcon: const Icon(
                            Icons.keyboard_alt_outlined,
                            color: kTextMuted,
                          ),
                          suffixIcon: IconButton(
                            tooltip: 'Soek profiel',
                            onPressed: _loading ? null : _submitManual,
                            icon: const Icon(
                              Icons.search_rounded,
                              color: kAccent,
                            ),
                          ),
                        ),
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
          'Toegang toegestaan',
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
          'Toegang geweier',
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
              title: 'Besoeker OTP',
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
                            hintText: 'Tik besoeker OTP',
                            keyboardType: TextInputType.number,
                            prefixIcon: const Icon(
                              Icons.password_rounded,
                              color: kTextMuted,
                              size: 18,
                            ),
                          ),
                          const SizedBox(height: 16),
                          GradientActionButton(
                            label: 'Verifieer OTP',
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
                              'GELDIGE BESOEKER',
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
                              'Genooi deur Steven Nel',
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
                                    label: 'Rede',
                                    value: 'Vergadering',
                                  ),
                                  const _VisitorDivider(),
                                  _VisitorInfoRow(
                                    label: 'OTP',
                                    value: _otpController.text.trim(),
                                  ),
                                  const _VisitorDivider(),
                                  const _VisitorInfoRow(
                                    label: 'Status',
                                    value: 'Hangend',
                                  ),
                                ],
                              ),
                            ),

                            const SizedBox(height: 18),

                            Row(
                              children: [
                                Expanded(
                                  child: GradientActionButton(
                                    label: 'Laat Toegang Toe',
                                    onTap: _allowEntry,
                                    height: 48,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: OutlineActionButton(
                                    label: 'Weier Toegang',
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