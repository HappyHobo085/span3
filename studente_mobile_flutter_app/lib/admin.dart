import 'package:flutter/material.dart';

import 'app_shared.dart';
import 'moon_api.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:nfc_manager/nfc_manager.dart';

/// Een ry vir die admin-lys: data kom van dieselfde bron as kampus.html (`POST /klasse` → `lokasies`).
class _AdminKlasRy {
  final int lokasieId;
  final String kampusNaam;
  final String klasNaam;
  final String beskrywing;

  _AdminKlasRy({
    required this.lokasieId,
    required this.kampusNaam,
    required this.klasNaam,
    required this.beskrywing,
  });
}

/// Admin-skerm: lys nuwe klasse (vanaf web kampus-bladsy), kies ry, skryf UID, verwyder ry.
class AdminHomePage extends StatefulWidget {
  const AdminHomePage({super.key});

  @override
  State<AdminHomePage> createState() => _AdminHomePageState();
}

class _AdminHomePageState extends State<AdminHomePage> {
  final List<_AdminKlasRy> _rye = [];
  int? _gekoseLokasieId;
  bool _laai = true;
  String? _fout;

  @override
  void initState() {
    super.initState();
    _herlaai();
  }

  Future<void> _herlaai() async {
    setState(() {
      _laai = true;
      _fout = null;
    });
    try {
      final kampusse = await MoonApi.fetchKampusse();
      final lokasies = await MoonApi.fetchLokasies();
      final idNaKampus = {
        for (final k in kampusse) k.kampusId: k.naam,
      };
      if (!mounted) return;
      setState(() {
        _rye
          ..clear()
          ..addAll(
            lokasies.map(
              (l) => _AdminKlasRy(
                lokasieId: l.id,
                kampusNaam: l.kampusId != null
                    ? (idNaKampus[l.kampusId!] ?? 'Kampus #${l.kampusId}')
                    : '—',
                klasNaam: l.naam.trim().isNotEmpty ? l.naam.trim() : '—',
                beskrywing: l.beskrywing?.trim().isNotEmpty == true
                    ? l.beskrywing!.trim()
                    : '—',
              ),
            ),
          );
        _gekoseLokasieId = null;
        _laai = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _fout = e.toString();
        _laai = false;
      });
    }
  }

  Future<void> _skryfUid() async {
  final id = _gekoseLokasieId;

  if (id == null) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Kies eers \'n klas in die lys.')),
    );
    return;
  }

  final uidController = TextEditingController();

  final ok = await showDialog<bool>(
    context: context,
    builder: (ctx) {
      return AlertDialog(
        backgroundColor: loginPageBackground,
        title: const Text(
          'Skryf UID na NFC tag',
          style: TextStyle(color: Colors.white),
        ),
        content: TextField(
          controller: uidController,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: 'UID vanaf databasis',
            labelStyle: const TextStyle(color: Colors.white70),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(color: Color(0xFF7B61FF)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(color: Color(0xFF00C2FF)),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Kanselleer'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Skryf'),
          ),
        ],
      );
    },
  );

  if (ok != true || !mounted) {
    uidController.dispose();
    return;
  }

  final uid = uidController.text.trim();
  uidController.dispose();

  if (uid.isEmpty) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('UID mag nie leeg wees nie.')),
    );
    return;
  }

  final available = await NfcManager.instance.isAvailable();

  if (!available) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('NFC is nie beskikbaar op hierdie toestel nie.')),
    );
    return;
  }

  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('Hou nou die NFC tag teen die foon...')),
  );

  NfcManager.instance.startSession(
    onDiscovered: (NfcTag tag) async {
      try {
        final ndef = Ndef.from(tag);

        if (ndef == null || !ndef.isWritable) {
          await NfcManager.instance.stopSession(
            errorMessage: 'Hierdie NFC tag kan nie geskryf word nie.',
          );
          return;
        }

        final message = NdefMessage([
          NdefRecord.createText(uid),
        ]);

        await ndef.write(message);

        await NfcManager.instance.stopSession(
          alertMessage: 'UID suksesvol geskryf!',
        );

        if (!mounted) return;

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('UID geskryf na NFC tag: $uid')),
        );
      } catch (e) {
        await NfcManager.instance.stopSession(
          errorMessage: 'Kon nie UID skryf nie.',
        );

        if (!mounted) return;

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Fout: $e')),
        );
      }
    },
  );
}

  @override
  Widget build(BuildContext context) {
    final wydte = MediaQuery.sizeOf(context).width;
    final paneelWydte = wydte > 560 ? 520.0 : wydte - 32;

    return Scaffold(
      backgroundColor: loginPageBackground,
      appBar: AppBar(
        backgroundColor: loginPageBackground,
        foregroundColor: Colors.white,
        title: const Text('Admin'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Herlaai',
            onPressed: _laai ? null : _herlaai,
          ),
        ],
      ),
      body: SafeArea(
        child: _laai
            ? const Center(
                child: CircularProgressIndicator(color: Color(0xFF7B61FF)),
              )
            : Column(
                children: [
                  if (_fout != null)
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(
                        _fout!,
                        style: const TextStyle(color: Colors.orangeAccent),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  Expanded(
                    child: Center(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: paneelWydte,
                              height: 400,
                              decoration: BoxDecoration(
                                color: loginPageBackground,
                                borderRadius: BorderRadius.circular(2),
                                border: Border.all(
                                  color: const Color(0xFF7B61FF),
                                  width: 1.5,
                                ),
                                boxShadow: const [
                                  BoxShadow(
                                    blurRadius: 18,
                                    spreadRadius: 1,
                                    color: Color(0x4D7B61FF),
                                    offset: Offset(0, 0),
                                  ),
                                ],
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  const Padding(
                                    padding: EdgeInsets.fromLTRB(
                                      16,
                                      14,
                                      16,
                                      8,
                                    ),
                                    child: Text(
                                      'Nuwe klasse (kampus)',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 18,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ),
                                  const Divider(
                                    height: 1,
                                    color: Color(0x337B61FF),
                                  ),
                                  Expanded(
                                    child: _rye.isEmpty
                                        ? const Center(
                                            child: Padding(
                                              padding: EdgeInsets.all(24),
                                              child: Text(
                                                'Geen klasse nie.\n'
                                                'Skep klasse op die kampus webblad; '
                                                'JWT (MoonApi.bearerToken) benodig vir /lokasies.',
                                                textAlign: TextAlign.center,
                                                style: TextStyle(
                                                  color: Colors.white70,
                                                ),
                                              ),
                                            ),
                                          )
                                        : ListView.builder(
                                            padding: const EdgeInsets.only(
                                              bottom: 8,
                                            ),
                                            itemCount: _rye.length,
                                            itemBuilder: (context, i) {
                                              final r = _rye[i];
                                              final gekies =
                                                  r.lokasieId ==
                                                  _gekoseLokasieId;
                                              return Material(
                                                color: gekies
                                                    ? const Color(0x337B61FF)
                                                    : Colors.transparent,
                                                child: InkWell(
                                                  onTap: () {
                                                    setState(() {
                                                      _gekoseLokasieId =
                                                          r.lokasieId;
                                                    });
                                                  },
                                                  child: Padding(
                                                    padding:
                                                        const EdgeInsets.symmetric(
                                                      horizontal: 14,
                                                      vertical: 12,
                                                    ),
                                                    child: Column(
                                                      crossAxisAlignment:
                                                          CrossAxisAlignment
                                                              .start,
                                                      children: [
                                                        Text(
                                                          r.kampusNaam,
                                                          style:
                                                              const TextStyle(
                                                            color: Color(
                                                              0xFF00C2FF,
                                                            ),
                                                            fontWeight:
                                                                FontWeight.w600,
                                                          ),
                                                        ),
                                                        const SizedBox(
                                                          height: 4,
                                                        ),
                                                        Text(
                                                          'Klas: ${r.klasNaam}',
                                                          style:
                                                              const TextStyle(
                                                            color: Colors.white,
                                                          ),
                                                        ),
                                                        const SizedBox(
                                                          height: 2,
                                                        ),
                                                        Text(
                                                          'Beskrywing: ${r.beskrywing}',
                                                          style:
                                                              const TextStyle(
                                                            color:
                                                                Colors.white70,
                                                            fontSize: 13,
                                                          ),
                                                        ),
                                                      ],
                                                    ),
                                                  ),
                                                ),
                                              );
                                            },
                                          ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 16),
                            SizedBox(
                              width: paneelWydte,
                              child: Align(
                                alignment: Alignment.centerRight,
                                child: GradientActionButton(
                                  label: 'Skryf UID',
                                  width: 200,
                                  onTap: _skryfUid,
                                ),
                              ),
                            ),
                          ],
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
