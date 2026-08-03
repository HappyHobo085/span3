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
  final TextEditingController _studentController = TextEditingController();
  final FocusNode _scannerFocusNode = FocusNode();

  bool _loading = false;
  String _status = 'Klik Scan QR of scan NFC';

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
    required String metode,
  }) async {
    final cleanNommer = nommer.trim();

    if (cleanNommer.isEmpty) {
      setState(() => _status = 'Geen nommer gelees nie');
      return;
    }

    setState(() {
      _loading = true;
      _status = 'Profiel laai...';
    });

    try {
      final profile = await MoonApi.wagteProfileScan(cleanNommer);

      if (!mounted) return;

      setState(() {
        _loading = false;
        _studentController.clear();
        _status = 'Profiel gevind';
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
            ? 'Scan suksesvol'
            : 'Gereed vir volgende scan';
      });

      FocusScope.of(context).requestFocus(_scannerFocusNode);
    } catch (e) {
      if (!mounted) return;

      final msg = e.toString().replaceFirst('Exception: ', '');

      setState(() {
        _loading = false;
        _status = msg;
      });

      FocusScope.of(context).requestFocus(_scannerFocusNode);
    }
  }

  void _startQrScan() {
    setState(() {
      _studentController.clear();
      _status = 'Scan QR nou...';
    });

    Future.delayed(const Duration(milliseconds: 150), () {
      if (mounted) {
        FocusScope.of(context).requestFocus(_scannerFocusNode);
      }
    });
  }

  Future<void> _scanStudentNfc() async {
    setState(() {
      _loading = true;
      _status = 'Hou student/personeel se tag teen MT90...';
    });

    try {
      await NfcManager.instance.startSession(
        onDiscovered: (tag) async {
          final nommer = _readNdefText(tag);
          debugPrint('NOMMER GELEES VIA NFC = [$nommer]');

          await NfcManager.instance.stopSession();

          if (!mounted) return;

          await _submitScan(
            nommer: nommer,
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

    if (clean.isEmpty || _loading) return;

    _submitScan(
      nommer: clean,
      metode: 'QR',
    );
  }

  Future<void> _openManualEntry() async {
    if (_loading) return;

    // Verwyder fokus eers van die versteekte QR-skandeerderveld.
    _scannerFocusNode.unfocus();
    FocusScope.of(context).unfocus();

    final nommer = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const _ManualEntryDialog(),
    );

    if (!mounted) return;

    if (nommer == null || nommer.trim().isEmpty) {
      Future.delayed(const Duration(milliseconds: 150), () {
        if (mounted) {
          FocusScope.of(context).requestFocus(_scannerFocusNode);
        }
      });
      return;
    }

    await _submitScan(
      nommer: nommer,
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
                          const Icon(
                            Icons.qr_code_scanner,
                            color: kAccent,
                            size: 54,
                          ),
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

                    GradientActionButton(
                      label: _loading ? 'Besig...' : 'Skandeer QR',
                      onTap: _loading ? () {} : _startQrScan,
                      height: 52,
                    ),

                    const SizedBox(height: 16),

                    GlassTapPanel(
                      label: _loading ? 'Besig...' : 'Skandeer NFC',
                      subtitle: 'Student / Personeel',
                      icon: '📡',
                      borderColor: const Color(0x3300C2FF),
                      onTap: _loading ? () {} : _scanStudentNfc,
                    ),

                    const SizedBox(height: 16),

                    GlassTapPanel(
                      label: _loading ? 'Besig...' : 'Tik Nommer Handmatig',
                      subtitle: 'Student / Personeel / ID',
                      icon: '⌨️',
                      borderColor: const Color(0x33FFB020),
                      onTap: _loading ? () {} : _openManualEntry,
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


class _ManualEntryDialog extends StatefulWidget {
  const _ManualEntryDialog();

  @override
  State<_ManualEntryDialog> createState() => _ManualEntryDialogState();
}

class _ManualEntryDialogState extends State<_ManualEntryDialog> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  String? _errorText;

  @override
  void initState() {
    super.initState();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _focusNode.requestFocus();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _submit() {
    final clean = _controller.text.trim();

    if (clean.isEmpty) {
      setState(() {
        _errorText = 'Tik eers ’n nommer in';
      });
      _focusNode.requestFocus();
      return;
    }

    Navigator.of(context).pop(clean);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF111827),
      title: const Text(
        'Handmatige Invoer',
        style: TextStyle(color: Colors.white),
      ),
      content: TextField(
        controller: _controller,
        focusNode: _focusNode,
        keyboardType: TextInputType.text,
        textInputAction: TextInputAction.done,
        autocorrect: false,
        enableSuggestions: false,
        style: GoogleFonts.inter(color: kText1),
        decoration: InputDecoration(
          labelText: 'Student-, personeel- of ID-nommer',
          labelStyle: GoogleFonts.inter(color: kTextMuted),
          hintText: 'Tik die nommer hier',
          hintStyle: GoogleFonts.inter(color: kTextMuted),
          errorText: _errorText,
          filled: true,
          fillColor: Colors.white10,
          prefixIcon: const Icon(
            Icons.badge_outlined,
            color: kTextMuted,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Colors.white24),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: Colors.white24),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(14),
            borderSide: const BorderSide(color: kAccent),
          ),
        ),
        onChanged: (_) {
          if (_errorText != null) {
            setState(() {
              _errorText = null;
            });
          }
        },
        onSubmitted: (_) => _submit(),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Kanselleer'),
        ),
        TextButton(
          onPressed: _submit,
          child: const Text(
            'Soek Profiel',
            style: TextStyle(color: kAccent),
          ),
        ),
      ],
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