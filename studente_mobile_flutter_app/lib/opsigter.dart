import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';
import 'profile_page.dart';

class OpsigterHomePage extends StatefulWidget {
  const OpsigterHomePage({super.key});

  @override
  State<OpsigterHomePage> createState() => _OpsigterHomePageState();
}

class _OpsigterHomePageState extends State<OpsigterHomePage> {
  int _selectedIndex = 0;

  void _onNavTap(int index) {
    if (index == 1) {
      Navigator.push(context, MaterialPageRoute(builder: (_) => const _KampusPage()));
      return;
    }
    if (index == 2) {
      Navigator.push(context, MaterialPageRoute(builder: (_) => const _KoshuisPage()));
      return;
    }
    setState(() => _selectedIndex = index);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 10),
            Expanded(
              child: _selectedIndex == 0 ? const _TuisTab() : const _ProfielTab(),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _OpsigterNavBar(
        selectedIndex: _selectedIndex,
        onTap: _onNavTap,
      ),
    );
  }
}

class _TuisTab extends StatefulWidget {
  const _TuisTab();

  @override
  State<_TuisTab> createState() => _TuisTabState();
}

class _TuisTabState extends State<_TuisTab> {
  bool _laai = true;
  String? _fout;
  Map<String, dynamic> _data = {};

  @override
  void initState() {
    super.initState();
    _laaiDashboard();
  }

  Future<void> _laaiDashboard() async {
    setState(() {
      _laai = true;
      _fout = null;
    });

    try {
      final result = await MoonApi.fetchLiveDashboard();

      if (!mounted) return;

      setState(() {
        _data = result;
        _laai = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _fout = e.toString().replaceFirst('Exception: ', '');
        _laai = false;
      });
    }
  }

  String _waarde(String sleutel) {
    if (_laai) return '—';
    return '${_data[sleutel] ?? 0}';
  }

  @override
  Widget build(BuildContext context) {
    final studente = _waarde('studente_op_kampus');
    final personeel = _waarde('personeel_op_kampus');
    final besoekers = _waarde('besoekers_vandag');
    final toegange = _waarde('toegange_vandag');

    return RefreshIndicator(
      onRefresh: _laaiDashboard,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Paneelbord',
              style: GoogleFonts.inter(
                color: kText1,
                fontSize: 24,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Kampusbeheer en monitering',
              style: GoogleFonts.inter(
                color: kTextMuted,
                fontSize: 12,
              ),
            ),

            if (_fout != null) ...[
              const SizedBox(height: 12),
              GlassCard(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 22),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Dashboard kon nie laai nie: $_fout',
                        style: GoogleFonts.inter(
                          color: kText2,
                          fontSize: 12,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: _laaiDashboard,
                      icon: const Icon(Icons.refresh_rounded, color: kAccent),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 18),

            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: Colors.green.withOpacity(0.14),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.green, width: 1.4),
              ),
              child: Row(
                children: [
                  const Icon(Icons.check_circle, color: Colors.green, size: 38),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'KAMPUS STATUS',
                          style: GoogleFonts.inter(
                            color: Colors.green,
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1.1,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Alles normaal',
                          style: GoogleFonts.inter(
                            color: kText1,
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Geen aktiewe noodgevalle nie',
                          style: GoogleFonts.inter(
                            color: kText2,
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: _laaiDashboard,
                    icon: const Icon(Icons.refresh_rounded, color: Colors.green),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 14),

            Row(
              children: [
                Expanded(
                  child: _OpsigterMetricCard(
                    label: 'STUDENTE',
                    value: studente,
                    subtitle: 'Op kampus',
                    icon: Icons.school_rounded,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _OpsigterMetricCard(
                    label: 'PERSONEEL',
                    value: personeel,
                    subtitle: 'Op kampus',
                    icon: Icons.badge_rounded,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 12),

            Row(
              children: [
                Expanded(
                  child: _OpsigterMetricCard(
                    label: 'BESOEKERS',
                    value: besoekers,
                    subtitle: 'Vandag',
                    icon: Icons.person_add_alt_1_rounded,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _OpsigterMetricCard(
                    label: 'TOEGANGE',
                    value: toegange,
                    subtitle: 'Vandag',
                    icon: Icons.qr_code_scanner_rounded,
                  ),
                ),
              ],
            ),

            const SizedBox(height: 16),

            GlassCard(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _SectionTitle('VINNIGE TOEGANG'),
                  const SizedBox(height: 12),
                  _QuickActionRow(
                    label: 'Kampus',
                    icon: Icons.location_city_rounded,
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const _KampusPage()),
                    ),
                  ),
                  const _ThinDivider(),
                  _QuickActionRow(
                    label: 'Koshuis',
                    icon: Icons.apartment_rounded,
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const _KoshuisPage()),
                    ),
                  ),
                  const _ThinDivider(),
                  _QuickActionRow(
                    label: 'Geleenthede',
                    icon: Icons.event_rounded,
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const _EventsPage()),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}


class _KampusPage extends StatefulWidget {
  const _KampusPage();

  @override
  State<_KampusPage> createState() => _KampusPageState();
}

class _KampusPageState extends State<_KampusPage> {
  bool _laai = true;
  String? _fout;
  List<KampusDto> _kampusse = [];
  KampusDto? _gekoseKampus;
  Map<String, dynamic> _status = {};

  @override
  void initState() {
    super.initState();
    _laaiKampusse();
  }

  Future<void> _laaiKampusse() async {
    setState(() {
      _laai = true;
      _fout = null;
    });

    try {
      final kampusse = await MoonApi.fetchOpsigterKampusse();

      if (!mounted) return;

      setState(() {
        _kampusse = kampusse;
        _gekoseKampus = kampusse.isNotEmpty ? kampusse.first : null;
      });

      if (_gekoseKampus?.kampusId != null) {
        await _laaiStatus(_gekoseKampus!.kampusId!);
      } else {
        if (!mounted) return;
        setState(() {
          _laai = false;
        });
      }
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _fout = e.toString().replaceFirst('Exception: ', '');
        _laai = false;
      });
    }
  }

  Future<void> _laaiStatus(int kampusId) async {
    setState(() {
      _laai = true;
      _fout = null;
    });

    try {
      final result = await MoonApi.fetchKampusStatus(kampusId);

      if (!mounted) return;

      setState(() {
        _status = result;
        _laai = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _fout = e.toString().replaceFirst('Exception: ', '');
        _laai = false;
      });
    }
  }

  List<Map<String, dynamic>> _lys(String key) {
    final raw = _status[key];

    if (raw is List) {
      return raw
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
    }

    return [];
  }

  int _telRol(List<Map<String, dynamic>> lys, String rol) {
    return lys.where((item) {
      final r = item['Rol_Naam']?.toString().toLowerCase() ?? '';
      return r == rol.toLowerCase();
    }).length;
  }

  String _naamVan(Map<String, dynamic> item) {
    final naam = item['GEB_Naam']?.toString() ?? '';
    final van = item['GEB_Van']?.toString() ?? '';
    final rol = item['Rol_Naam']?.toString() ?? '';
    final fullName = '$naam $van'.trim();

    if (fullName.isEmpty && rol.isEmpty) return 'Onbekende persoon';
    if (rol.isEmpty) return fullName;
    return '$fullName · $rol';
  }

  String _detail(Map<String, dynamic> item) {
  final rigting = item['Rigting']?.toString() ?? '';
  final metode = item['Metode']?.toString() ?? '';
  final tyd = item['Tydstempel']?.toString() ?? '';

  String kortTyd = '';

  if (tyd.isNotEmpty) {
    try {
      final dt = DateTime.parse(tyd).add(
        const Duration(hours: 2),
      );

      final uur = dt.hour.toString().padLeft(2, '0');
      final minuut = dt.minute.toString().padLeft(2, '0');

      kortTyd = '$uur:$minuut';
    } catch (_) {
      kortTyd = tyd.length >= 16 ? tyd.substring(11, 16) : tyd;
    }
  }

  return [rigting, metode, kortTyd]
      .where((v) => v.trim().isNotEmpty)
      .join(' · ');
}

  @override
  Widget build(BuildContext context) {
    final scannedIn = _lys('scanned_in');
    final scannedOut = _lys('scanned_out');

    final studenteIn = _telRol(scannedIn, 'Student');
    final personeelIn = _telRol(scannedIn, 'Personeel');
    final studenteOut = _telRol(scannedOut, 'Student');
    final personeelOut = _telRol(scannedOut, 'Personeel');

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Kampus',
              subtitle: 'Regstreekse kampusoorsig',
              showBack: true,
            ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: () async {
                  if (_gekoseKampus?.kampusId != null) {
                    await _laaiStatus(_gekoseKampus!.kampusId!);
                  } else {
                    await _laaiKampusse();
                  }
                },
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      GlassCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _SectionTitle('KIES KAMPUS'),
                            const SizedBox(height: 12),
                            DropdownButtonHideUnderline(
                              child: DropdownButton<KampusDto>(
                                value: _gekoseKampus,
                                isExpanded: true,
                                dropdownColor: const Color(0xFF111827),
                                iconEnabledColor: kAccent,
                                hint: Text(
                                  'Kies kampus',
                                  style: GoogleFonts.inter(
                                    color: kTextMuted,
                                    fontSize: 13,
                                  ),
                                ),
                                items: _kampusse.map((kampus) {
                                  return DropdownMenuItem<KampusDto>(
                                    value: kampus,
                                    child: Text(
                                      kampus.naam,
                                      overflow: TextOverflow.ellipsis,
                                      style: GoogleFonts.inter(
                                        color: kText1,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  );
                                }).toList(),
                                onChanged: (kampus) {
                                  if (kampus == null) return;

                                  setState(() {
                                    _gekoseKampus = kampus;
                                  });

                                  if (kampus.kampusId != null) {
                                    _laaiStatus(kampus.kampusId!);
                                  }
                                },
                              ),
                            ),
                          ],
                        ),
                      ),

                      if (_fout != null) ...[
                        const SizedBox(height: 14),
                        GlassCard(
                          padding: const EdgeInsets.all(12),
                          child: Row(
                            children: [
                              const Icon(
                                Icons.warning_amber_rounded,
                                color: Colors.orange,
                                size: 22,
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  _fout!,
                                  style: GoogleFonts.inter(
                                    color: kText2,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                              IconButton(
                                onPressed: _laaiKampusse,
                                icon: const Icon(
                                  Icons.refresh_rounded,
                                  color: kAccent,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],

                      const SizedBox(height: 14),

                      Row(
                        children: [
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'STUDENTE',
                              value: _laai ? '—' : '$studenteIn',
                              subtitle: 'In kampus',
                              icon: Icons.school_rounded,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'PERSONEEL',
                              value: _laai ? '—' : '$personeelIn',
                              subtitle: 'In kampus',
                              icon: Icons.badge_rounded,
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 12),

                      Row(
                        children: [
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'STUDENTE UIT',
                              value: _laai ? '—' : '$studenteOut',
                              subtitle: 'Uit kampus',
                              icon: Icons.logout_rounded,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'PERS. UIT',
                              value: _laai ? '—' : '$personeelOut',
                              subtitle: 'Uit kampus',
                              icon: Icons.exit_to_app_rounded,
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 14),

                      GlassCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _SectionTitle('AKTIEWE BEWEGING'),
                            const SizedBox(height: 12),
                            if (_laai)
                              const Center(child: CircularProgressIndicator())
                            else if (scannedIn.isEmpty)
                              const _MiniLogRow(
                                name: 'Geen aktiewe beweging',
                                detail: 'Kampus beweging sal hier verskyn.',
                                icon: Icons.timeline_rounded,
                              )
                            else
                              Column(
                                children: scannedIn.take(6).map((item) {
                                  return Padding(
                                    padding: const EdgeInsets.only(bottom: 10),
                                    child: _MiniLogRow(
                                      name: _naamVan(item),
                                      detail: _detail(item),
                                      icon: Icons.login_rounded,
                                    ),
                                  );
                                }).toList(),
                              ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 14),

                      GlassCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _SectionTitle('AKSIES'),
                            const SizedBox(height: 12),
                            _QuickActionRow(
                              label: 'Soek persoon op kampus',
                              icon: Icons.search_rounded,
                              onTap: () => _showComingSoon(context),
                            ),
                            const _ThinDivider(),
                            _QuickActionRow(
                              label: 'Verfris kampusdata',
                              icon: Icons.refresh_rounded,
                              onTap: () {
                                if (_gekoseKampus?.kampusId != null) {
                                  _laaiStatus(_gekoseKampus!.kampusId!);
                                }
                              },
                            ),
                          ],
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



class _KoshuisPage extends StatefulWidget {
  const _KoshuisPage();

  @override
  State<_KoshuisPage> createState() => _KoshuisPageState();
}

class _KoshuisPageState extends State<_KoshuisPage> {
  bool _laai = true;
  String? _fout;
  List<KoshuisDto> _koshuise = [];
  KoshuisDto? _gekoseKoshuis;
  Map<String, dynamic> _status = {};

  @override
  void initState() {
    super.initState();
    _laaiKoshuise();
  }

  Future<void> _laaiKoshuise() async {
    setState(() {
      _laai = true;
      _fout = null;
    });

    try {
      final koshuise = await MoonApi.fetchKoshuise();

      if (!mounted) return;

      setState(() {
        _koshuise = koshuise;
        _gekoseKoshuis = koshuise.isNotEmpty ? koshuise.first : null;
      });

      if (_gekoseKoshuis?.koshuisId != null) {
        await _laaiStatus(_gekoseKoshuis!.koshuisId!);
      } else {
        if (!mounted) return;
        setState(() {
          _laai = false;
        });
      }
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _fout = e.toString().replaceFirst('Exception: ', '');
        _laai = false;
      });
    }
  }

  Future<void> _laaiStatus(int koshuisId) async {
    setState(() {
      _laai = true;
      _fout = null;
    });

    try {
      final result = await MoonApi.fetchKoshuisStatus(koshuisId);

      if (!mounted) return;

      setState(() {
        _status = result;
        _laai = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _fout = e.toString().replaceFirst('Exception: ', '');
        _laai = false;
      });
    }
  }

  List<Map<String, dynamic>> _lys(String key) {
    final raw = _status[key];

    if (raw is List) {
      return raw
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
    }

    return [];
  }

  int _intValue(List<String> keys) {
    for (final key in keys) {
      final value = _status[key];
      if (value is int) return value;
      if (value is num) return value.toInt();
      if (value != null) {
        final parsed = int.tryParse(value.toString());
        if (parsed != null) return parsed;
      }
    }
    return 0;
  }

  String _naamVan(Map<String, dynamic> item) {
    final naam = item['GEB_Naam']?.toString() ??
        item['naam']?.toString() ??
        item['Naam']?.toString() ??
        '';
    final van = item['GEB_Van']?.toString() ??
        item['van']?.toString() ??
        item['Van']?.toString() ??
        '';
    final rol = item['Rol_Naam']?.toString() ??
        item['rol']?.toString() ??
        item['Rol']?.toString() ??
        '';

    final fullName = '$naam $van'.trim();

    if (fullName.isEmpty && rol.isEmpty) return 'Onbekende persoon';
    if (rol.isEmpty) return fullName;
    return '$fullName · $rol';
  }

  String _detail(Map<String, dynamic> item) {
    final rigting = item['Rigting']?.toString() ??
        item['rigting']?.toString() ??
        '';
    final metode = item['Metode']?.toString() ??
        item['metode']?.toString() ??
        '';
    final tyd = item['Tydstempel']?.toString() ??
        item['tyd']?.toString() ??
        item['timestamp']?.toString() ??
        '';

    final kortTyd = tyd.length >= 16 ? tyd.substring(11, 16) : tyd;

    return [rigting, metode, kortTyd]
        .where((v) => v.trim().isNotEmpty)
        .join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    final scannedIn = _lys('scanned_in');
    final scannedOut = _lys('scanned_out');

    final inCount = _intValue([
      'scanned_in_count',
      'students_in',
      'studente_in',
      'inwoners_in',
      'current_residents',
      'huidige_inwoners',
    ]);
    final outCount = _intValue([
      'scanned_out_count',
      'students_out',
      'studente_out',
      'inwoners_out',
    ]);
    final kapasiteit = _intValue([
      'capacity',
      'kapasiteit',
      'KOS_Kapasiteit',
      'Kapasiteit',
    ]);
    final inwoners = _intValue([
      'current_residents',
      'residents',
      'inwoners',
      'huidige_inwoners',
    ]);

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Koshuis',
              subtitle: 'Koshuis oorsig',
              showBack: true,
            ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: () async {
                  if (_gekoseKoshuis?.koshuisId != null) {
                    await _laaiStatus(_gekoseKoshuis!.koshuisId!);
                  } else {
                    await _laaiKoshuise();
                  }
                },
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    children: [
                      GlassCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _SectionTitle('KIES KOSHUIS'),
                            const SizedBox(height: 12),
                            DropdownButtonHideUnderline(
                              child: DropdownButton<KoshuisDto>(
                                value: _gekoseKoshuis,
                                isExpanded: true,
                                dropdownColor: const Color(0xFF111827),
                                iconEnabledColor: kAccent,
                                hint: Text(
                                  _laai ? 'Laai koshuise...' : 'Kies koshuis',
                                  style: GoogleFonts.inter(
                                    color: kTextMuted,
                                    fontSize: 13,
                                  ),
                                ),
                                items: _koshuise.map((koshuis) {
                                  return DropdownMenuItem<KoshuisDto>(
                                    value: koshuis,
                                    child: Text(
                                      koshuis.naam,
                                      overflow: TextOverflow.ellipsis,
                                      style: GoogleFonts.inter(
                                        color: kText1,
                                        fontSize: 13,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  );
                                }).toList(),
                                onChanged: (koshuis) {
                                  if (koshuis == null) return;

                                  setState(() {
                                    _gekoseKoshuis = koshuis;
                                  });

                                  if (koshuis.koshuisId != null) {
                                    _laaiStatus(koshuis.koshuisId!);
                                  }
                                },
                              ),
                            ),
                          ],
                        ),
                      ),

                      if (_fout != null) ...[
                        const SizedBox(height: 14),
                        GlassCard(
                          padding: const EdgeInsets.all(12),
                          child: Row(
                            children: [
                              const Icon(
                                Icons.warning_amber_rounded,
                                color: Colors.orange,
                                size: 22,
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  _fout!,
                                  style: GoogleFonts.inter(
                                    color: kText2,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                              IconButton(
                                onPressed: _laaiKoshuise,
                                icon: const Icon(
                                  Icons.refresh_rounded,
                                  color: kAccent,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],

                      const SizedBox(height: 14),

                      Row(
                        children: [
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'INWONERS',
                              value: _laai ? '—' : '${inCount == 0 && scannedIn.isNotEmpty ? scannedIn.length : inCount}',
                              subtitle: 'In koshuis',
                              icon: Icons.bed_rounded,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'UIT',
                              value: _laai ? '—' : '${outCount == 0 && scannedOut.isNotEmpty ? scannedOut.length : outCount}',
                              subtitle: 'Uit koshuis',
                              icon: Icons.logout_rounded,
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 12),

                      Row(
                        children: [
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'KAPASITEIT',
                              value: _laai ? '—' : '$kapasiteit',
                              subtitle: 'Totale plekke',
                              icon: Icons.apartment_rounded,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'HUIDIG',
                              value: _laai ? '—' : '$inwoners',
                              subtitle: 'Inwoners',
                              icon: Icons.people_rounded,
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 14),

                      GlassCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _SectionTitle('KOSHUIS STATUS'),
                            const SizedBox(height: 12),
                            if (_laai)
                              const Center(child: CircularProgressIndicator())
                            else if (scannedIn.isEmpty)
                              const _MiniLogRow(
                                name: 'Geen aktiewe inwoners',
                                detail: 'Koshuis beweging sal hier verskyn.',
                                icon: Icons.check_circle,
                              )
                            else
                              Column(
                                children: scannedIn.take(6).map((item) {
                                  return Padding(
                                    padding: const EdgeInsets.only(bottom: 10),
                                    child: _MiniLogRow(
                                      name: _naamVan(item),
                                      detail: _detail(item),
                                      icon: Icons.login_rounded,
                                    ),
                                  );
                                }).toList(),
                              ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 14),

                      GlassCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const _SectionTitle('AKSIES'),
                            const SizedBox(height: 12),
                            _QuickActionRow(
                              label: 'Soek inwoner',
                              icon: Icons.search_rounded,
                              onTap: () => _showComingSoon(context),
                            ),
                            const _ThinDivider(),
                            _QuickActionRow(
                              label: 'Verfris koshuisdata',
                              icon: Icons.refresh_rounded,
                              onTap: () {
                                if (_gekoseKoshuis?.koshuisId != null) {
                                  _laaiStatus(_gekoseKoshuis!.koshuisId!);
                                }
                              },
                            ),
                          ],
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


class _EventsPage extends StatelessWidget {
  const _EventsPage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(title: 'Geleenthede', subtitle: 'Kampusgeleenthede', showBack: true),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Row(
                      children: const [
                        Expanded(child: _OpsigterMetricCard(label: 'GELEENTHEDE', value: '0', subtitle: 'Aktief', icon: Icons.event_rounded)),
                        SizedBox(width: 12),
                        Expanded(child: _OpsigterMetricCard(label: 'TOEGANGE', value: '0', subtitle: 'Vandag', icon: Icons.qr_code_scanner_rounded)),
                      ],
                    ),
                    const SizedBox(height: 14),
                    const _InfoGlassCard(title: 'AKTIEWE GELEENTHEDE', name: 'Geen aktiewe geleenthede', detail: 'Geleenthede sal hier verskyn wanneer dit geskep word.', icon: Icons.event_busy_rounded),
                    const SizedBox(height: 14),
                    GlassCard(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const _SectionTitle('AKSIES'),
                          const SizedBox(height: 12),
                          _QuickActionRow(label: 'Skep Geleentheid', icon: Icons.add_circle_outline_rounded, onTap: () => _showComingSoon(context)),
                          const _ThinDivider(),
                          _QuickActionRow(label: 'Geleentheid-toegang', icon: Icons.qr_code_2_rounded, onTap: () => _showComingSoon(context)),
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

class _ProfielTab extends StatelessWidget {
  const _ProfielTab();

  @override
  Widget build(BuildContext context) {
    return const ProfilePage();
  }
}

class _InfoGlassCard extends StatelessWidget {
  final String title;
  final String name;
  final String detail;
  final IconData icon;

  const _InfoGlassCard({required this.title, required this.name, required this.detail, required this.icon});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(title),
          const SizedBox(height: 12),
          _MiniLogRow(name: name, detail: detail, icon: icon),
        ],
      ),
    );
  }
}

class _OpsigterMetricCard extends StatelessWidget {
  final String label;
  final String value;
  final String subtitle;
  final IconData icon;

  const _OpsigterMetricCard({required this.label, required this.value, required this.subtitle, required this.icon});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: kAccent, size: 24),
          const SizedBox(height: 10),
          Text(label, style: GoogleFonts.inter(color: kTextMuted, fontSize: 9, fontWeight: FontWeight.w800, letterSpacing: 1.1)),
          const SizedBox(height: 6),
          Text(value, style: GoogleFonts.inter(color: kText1, fontSize: 30, fontWeight: FontWeight.w900, height: 1)),
          const SizedBox(height: 6),
          Text(subtitle, style: GoogleFonts.inter(color: kText2, fontSize: 11)),
        ],
      ),
    );
  }
}

class _QuickActionRow extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback onTap;

  const _QuickActionRow({required this.label, required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Row(
          children: [
            Icon(icon, color: kAccent, size: 20),
            const SizedBox(width: 12),
            Expanded(child: Text(label, style: GoogleFonts.inter(color: kText2, fontSize: 13, fontWeight: FontWeight.w600))),
            const Icon(Icons.chevron_right_rounded, color: kTextMuted, size: 20),
          ],
        ),
      ),
    );
  }
}

class _MiniLogRow extends StatelessWidget {
  final String name;
  final String detail;
  final IconData icon;

  const _MiniLogRow({required this.name, required this.detail, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: kAccent, size: 22),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(name, style: GoogleFonts.inter(color: kText1, fontSize: 13, fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              Text(detail, style: GoogleFonts.inter(color: kTextMuted, fontSize: 11)),
            ],
          ),
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String text;
  const _SectionTitle(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(text, style: GoogleFonts.inter(color: kTextMuted, fontSize: 9, fontWeight: FontWeight.w800, letterSpacing: 1.1));
  }
}

class _ThinDivider extends StatelessWidget {
  const _ThinDivider();

  @override
  Widget build(BuildContext context) {
    return const Divider(color: Color(0x0AFFFFFF), height: 1);
  }
}

void _showComingSoon(BuildContext context) {
  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Funksie kom later')));
}

class _OpsigterNavBar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onTap;

  const _OpsigterNavBar({required this.selectedIndex, required this.onTap});

  @override
  Widget build(BuildContext context) {
    const items = [
      _NavItem(icon: Icons.dashboard_rounded, label: 'Paneelbord'),
      _NavItem(icon: Icons.location_city_rounded, label: 'Kampus'),
      _NavItem(icon: Icons.apartment_rounded, label: 'Koshuis'),
      _NavItem(icon: Icons.person_rounded, label: 'Profiel'),
    ];

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0D1120),
        border: const Border(top: BorderSide(color: Color(0x1AFFFFFF), width: 1)),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.4), blurRadius: 20, offset: const Offset(0, -4))],
      ),
      padding: EdgeInsets.only(top: 10, bottom: MediaQuery.of(context).padding.bottom + 10),
      child: Row(
        children: List.generate(items.length, (i) {
          final active = i == selectedIndex;
          return Expanded(
            child: GestureDetector(
              onTap: () => onTap(i),
              behavior: HitTestBehavior.opaque,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: active ? 28 : 0,
                    height: 2,
                    margin: const EdgeInsets.only(bottom: 6),
                    decoration: BoxDecoration(color: active ? kAccent : Colors.transparent, borderRadius: BorderRadius.circular(1)),
                  ),
                  Icon(items[i].icon, size: 22, color: active ? kAccent : kTextMuted),
                  const SizedBox(height: 4),
                  Text(items[i].label, style: GoogleFonts.inter(color: active ? kText1 : kTextMuted, fontSize: 10, fontWeight: active ? FontWeight.w600 : FontWeight.w400)),
                ],
              ),
            ),
          );
        }),
      ),
    );
  }
}

class _NavItem {
  final IconData icon;
  final String label;
  const _NavItem({required this.icon, required this.label});
}
