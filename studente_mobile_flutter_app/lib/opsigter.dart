import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:share_plus/share_plus.dart';
import 'dart:async';
import 'app_shared.dart';
import 'moon_api.dart';
import 'profile_page.dart';


ThemeData _moonPickerTheme(BuildContext context) {
  final base = Theme.of(context);

  return base.copyWith(
    brightness: Brightness.dark,
    colorScheme: base.colorScheme.copyWith(
      brightness: Brightness.dark,
      primary: kAccent,
      onPrimary: Colors.black,
      surface: const Color(0xFF0F172A),
      onSurface: Colors.white,
    ),
    datePickerTheme: const DatePickerThemeData(
      backgroundColor: Color(0xFF0F172A),
      surfaceTintColor: Colors.transparent,
      headerBackgroundColor: Color(0xFF111827),
      headerForegroundColor: Colors.white,
      dividerColor: Color(0xFF334155),
    ),
    timePickerTheme: const TimePickerThemeData(
      backgroundColor: Color(0xFF0F172A),
      hourMinuteColor: Color(0xFF1E293B),
      hourMinuteTextColor: Colors.white,
      dialBackgroundColor: Color(0xFF111827),
      dialHandColor: kAccent,
      dialTextColor: Colors.white,
      entryModeIconColor: kAccent,
      dayPeriodColor: Color(0xFF1E293B),
      dayPeriodTextColor: Colors.white,
    ),
  );
}


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
    if (index == 3) {
      Navigator.push(context, MaterialPageRoute(builder: (_) => const _NoodPage()));
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
              'Dashboard',
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
                        'Paneelbord kon nie laai nie: $_fout',
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
                  const _SectionTitle('VINNIGE AKSIES'),
                  const SizedBox(height: 12),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final available = constraints.maxWidth;
                      final columns = available >= 620
                          ? 4
                          : available >= 360
                              ? 2
                              : 1;
                      final tileWidth =
                          (available - ((columns - 1) * 12)) / columns;

                      return Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          SizedBox(
                            width: tileWidth,
                            child: _OpsigterQuickActionCard(
                              icon: Icons.location_city_rounded,
                              label: 'Kampus',
                              subtitle: 'Kampusoorsig',
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => const _KampusPage(),
                                ),
                              ),
                            ),
                          ),
                          SizedBox(
                            width: tileWidth,
                            child: _OpsigterQuickActionCard(
                              icon: Icons.apartment_rounded,
                              label: 'Koshuis',
                              subtitle: 'Koshuisoorsig',
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => const _KoshuisPage(),
                                ),
                              ),
                            ),
                          ),
                          SizedBox(
                            width: tileWidth,
                            child: _OpsigterQuickActionCard(
                              icon: Icons.event_rounded,
                              label: 'Events',
                              subtitle: 'Bestuur events',
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => const _EventsPage(),
                                ),
                              ),
                            ),
                          ),
                          SizedBox(
                            width: tileWidth,
                            child: _OpsigterQuickActionCard(
                              icon: Icons.emergency_rounded,
                              label: 'Nood',
                              subtitle: 'Noodbeheer',
                              danger: true,
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => const _NoodPage(),
                                ),
                              ),
                            ),
                          ),
                        ],
                      );
                    },
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
  List<Map<String, dynamic>> _besoekers = [];
  List<MoonEventDto> _kampusEvents = [];

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
      _status = {};
      _besoekers = [];
      _kampusEvents = [];
    });

    try {
      final resultate = await Future.wait<dynamic>([
        MoonApi.fetchKampusStatus(kampusId),
        MoonApi.fetchOpsigterKampusBesoekers(kampusId),
        MoonApi.fetchEvents(view: 'komende'),
      ]);

      if (!mounted) return;

      final status = Map<String, dynamic>.from(resultate[0] as Map);
      final besoekers = List<Map<String, dynamic>>.from(resultate[1] as List);
      final alleEvents = List<MoonEventDto>.from(resultate[2] as List);
      final kampusEvents = alleEvents
          .where((event) => event.kampusId == kampusId)
          .toList();

      setState(() {
        _status = status;
        _besoekers = besoekers;
        _kampusEvents = kampusEvents;
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

  List<Map<String, dynamic>> _rolLys(
    List<Map<String, dynamic>> lys,
    String rol,
  ) {
    return lys.where((item) {
      final r = item['Rol_Naam']?.toString().toLowerCase() ?? '';
      return r == rol.toLowerCase();
    }).toList();
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
    final studenteLys = _rolLys(scannedIn, 'Student');
    final personeelLys = _rolLys(scannedIn, 'Personeel');

    final studenteIn = studenteLys.length;
    final personeelIn = personeelLys.length;
    final besoekersVandag = _besoekers.length;
    final eventsKomende = _kampusEvents.length;
    final kampusNaam = _gekoseKampus?.naam ?? 'Kampus';
    final kampusId = _gekoseKampus?.kampusId;

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
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => _KampusPeopleListPage(
                                    title: 'Studente in Kampus',
                                    kampusNaam: kampusNaam,
                                    items: studenteLys,
                                    emptyText: 'Geen studente is tans op kampus nie.',
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'PERSONEEL',
                              value: _laai ? '—' : '$personeelIn',
                              subtitle: 'In kampus',
                              icon: Icons.badge_rounded,
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => _KampusPeopleListPage(
                                    title: 'Personeel in Kampus',
                                    kampusNaam: kampusNaam,
                                    items: personeelLys,
                                    emptyText: 'Geen personeel is tans op kampus nie.',
                                  ),
                                ),
                              ),
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
                              value: _laai ? '—' : '$besoekersVandag',
                              subtitle: 'Vandag',
                              icon: Icons.person_add_alt_1_rounded,
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (_) => _KampusBesoekersPage(
                                    kampusNaam: kampusNaam,
                                    items: _besoekers,
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'EVENTS',
                              value: _laai ? '—' : '$eventsKomende',
                              subtitle: 'Komende',
                              icon: Icons.event_rounded,
                              onTap: kampusId == null
                                  ? null
                                  : () => Navigator.push(
                                        context,
                                        MaterialPageRoute(
                                          builder: (_) => _EventsPage(
                                            kampusId: kampusId,
                                            kampusNaam: kampusNaam,
                                          ),
                                        ),
                                      ),
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


class _KampusPeopleListPage extends StatelessWidget {
  final String title;
  final String kampusNaam;
  final List<Map<String, dynamic>> items;
  final String emptyText;

  const _KampusPeopleListPage({
    required this.title,
    required this.kampusNaam,
    required this.items,
    required this.emptyText,
  });

  String _naam(Map<String, dynamic> item) {
    final naam = item['GEB_Naam']?.toString() ?? '';
    final van = item['GEB_Van']?.toString() ?? '';
    final full = '$naam $van'.trim();
    return full.isEmpty ? 'Onbekende persoon' : full;
  }

  String _detail(Map<String, dynamic> item) {
    final rol = item['Rol_Naam']?.toString() ?? '';
    final metode = item['Metode']?.toString() ?? '';
    final tydRaw = item['Tydstempel']?.toString() ?? '';
    String tyd = '';
    if (tydRaw.isNotEmpty) {
      try {
        final dt = DateTime.parse(tydRaw).add(const Duration(hours: 2));
        tyd = '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
      } catch (_) {}
    }
    return [rol, 'IN', metode, tyd].where((v) => v.trim().isNotEmpty).join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(title: title, subtitle: kampusNaam, showBack: true),
            Expanded(
              child: items.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Text(
                          emptyText,
                          textAlign: TextAlign.center,
                          style: GoogleFonts.inter(color: kTextMuted, fontSize: 13),
                        ),
                      ),
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: items.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 10),
                      itemBuilder: (context, index) {
                        final item = items[index];
                        return GlassCard(
                          padding: const EdgeInsets.all(14),
                          child: _MiniLogRow(
                            name: _naam(item),
                            detail: _detail(item),
                            icon: Icons.person_rounded,
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _KampusBesoekersPage extends StatelessWidget {
  final String kampusNaam;
  final List<Map<String, dynamic>> items;

  const _KampusBesoekersPage({
    required this.kampusNaam,
    required this.items,
  });

  String _naam(Map<String, dynamic> item) {
    final naam = item['naam']?.toString() ?? '';
    final van = item['van']?.toString() ?? '';
    final full = '$naam $van'.trim();
    return full.isEmpty ? 'Onbekende besoeker' : full;
  }

  String _detail(Map<String, dynamic> item) {
    final selfoon = item['selfoon']?.toString() ?? '';
    final gasheer = item['gasheer_naam']?.toString() ?? '';
    final rede = item['rede']?.toString() ?? '';
    final tydRaw = item['besluit_op']?.toString() ?? '';
    String tyd = '';
    if (tydRaw.isNotEmpty) {
      try {
        final parsed = DateTime.parse(tydRaw);
        final dt = parsed.isUtc ? parsed.toLocal() : parsed.add(const Duration(hours: 2));
        tyd = '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
      } catch (_) {}
    }
    return [
      if (gasheer.isNotEmpty) 'Gasheer: $gasheer',
      if (selfoon.isNotEmpty) selfoon,
      if (rede.isNotEmpty) rede,
      if (tyd.isNotEmpty) 'Toegelaat $tyd',
    ].join(' · ');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Besoekers',
              subtitle: '$kampusNaam · vandag',
              showBack: true,
            ),
            Expanded(
              child: items.isEmpty
                  ? Center(
                      child: Text(
                        'Geen besoekers is vandag toegelaat nie.',
                        style: GoogleFonts.inter(color: kTextMuted, fontSize: 13),
                      ),
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.all(16),
                      itemCount: items.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 10),
                      itemBuilder: (context, index) {
                        final item = items[index];
                        return GlassCard(
                          padding: const EdgeInsets.all(14),
                          child: _MiniLogRow(
                            name: _naam(item),
                            detail: _detail(item),
                            icon: Icons.person_add_alt_1_rounded,
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NoodPage extends StatelessWidget {
  const _NoodPage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Nood',
              subtitle: 'Kampus noodbeheer',
              showBack: true,
            ),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: Colors.red.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(
                          color: Colors.red.withOpacity(0.8),
                          width: 1.4,
                        ),
                      ),
                      child: Column(
                        children: [
                          const Icon(
                            Icons.emergency_rounded,
                            color: Colors.red,
                            size: 52,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'NOODSTELSEL',
                            style: GoogleFonts.inter(
                              color: Colors.red,
                              fontSize: 11,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 1.3,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Geen aktiewe noodgeval',
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 20,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Die noodsein en sirene word later aan Firebase gekoppel.',
                            textAlign: TextAlign.center,
                            style: GoogleFonts.inter(
                              color: kText2,
                              fontSize: 12,
                              height: 1.4,
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
                          const _SectionTitle('NOODAKSIE'),
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            height: 56,
                            child: ElevatedButton.icon(
                              onPressed: null,
                              icon: const Icon(Icons.warning_amber_rounded),
                              label: Text(
                                'AKTIVEER NOOD',
                                style: GoogleFonts.inter(
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: 0.5,
                                ),
                              ),
                              style: ElevatedButton.styleFrom(
                                disabledBackgroundColor:
                                    Colors.red.withOpacity(0.28),
                                disabledForegroundColor:
                                    Colors.white.withOpacity(0.55),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(16),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            'Die knoppie bly vir nou gedeaktiveer totdat ons die noodsein, sirene en toestelkennisgewings koppel.',
                            style: GoogleFonts.inter(
                              color: kTextMuted,
                              fontSize: 11,
                              height: 1.4,
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


class _EventsPage extends StatefulWidget {
  final int? kampusId;
  final String? kampusNaam;

  const _EventsPage({this.kampusId, this.kampusNaam});

  @override
  State<_EventsPage> createState() => _EventsPageState();
}

class _EventsPageState extends State<_EventsPage> {
  bool _loading = true;
  String? _error;
  String _view = 'komende';
  List<MoonEventDto> _events = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final allEvents = await MoonApi.fetchEvents(view: _view);
      final events = widget.kampusId == null
          ? [...allEvents]
          : allEvents
              .where((event) => event.kampusId == widget.kampusId)
              .toList();
      events.sort((a, b) => _view == 'vorige'
          ? b.beginTyd.compareTo(a.beginTyd)
          : a.beginTyd.compareTo(b.beginTyd));
      if (!mounted) return;
      setState(() {
        _events = events;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  void _setView(String view) {
    if (_view == view) return;
    setState(() => _view = view);
    _load();
  }

  String _date(DateTime dt) {
    const months = [
      'Jan', 'Feb', 'Mrt', 'Apr', 'Mei', 'Jun',
      'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Des'
    ];
    return '${dt.day} ${months[dt.month - 1]} ${dt.year}';
  }

  String _time(DateTime dt) =>
      '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';

  Future<void> _create() async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const _EventFormPage()),
    );
    if (changed == true) await _load();
  }

  Future<void> _manage(MoonEventDto event) async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => _OpsigterEventDetailPage(event: event),
      ),
    );
    if (changed == true) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final isPrevious = _view == 'vorige';
    final totalRsvp = _events.fold<int>(0, (sum, e) => sum + e.rsvpAantal);
    final scopeText = widget.kampusNaam == null ? '' : '${widget.kampusNaam} · ';

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Events',
              subtitle: '$scopeText${isPrevious ? 'vorige events & statistiek' : 'skep en bestuur kampus-events'}',
              showBack: true,
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Row(
                children: [
                  _OpsigterEventFilterButton(
                    label: 'Komende',
                    active: !isPrevious,
                    onTap: () => _setView('komende'),
                  ),
                  const SizedBox(width: 10),
                  _OpsigterEventFilterButton(
                    label: 'Vorige',
                    active: isPrevious,
                    onTap: () => _setView('vorige'),
                  ),
                ],
              ),
            ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: _load,
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(16),
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: _OpsigterMetricCard(
                            label: 'EVENTS',
                            value: _loading ? '—' : '${_events.length}',
                            subtitle: isPrevious ? 'Vorige' : 'Komende',
                            icon: Icons.event_rounded,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _OpsigterMetricCard(
                            label: 'RSVP',
                            value: _loading ? '—' : '$totalRsvp',
                            subtitle: 'Totaal',
                            icon: Icons.how_to_reg_rounded,
                          ),
                        ),
                      ],
                    ),
                    if (!isPrevious) ...[
                      const SizedBox(height: 14),
                      GradientActionButton(
                        label: 'Skep Nuwe Event',
                        onTap: _create,
                        height: 52,
                      ),
                    ],
                    const SizedBox(height: 16),
                    if (_error != null)
                      GlassCard(
                        padding: const EdgeInsets.all(14),
                        child: Text(
                          _error!,
                          style: GoogleFonts.inter(color: Colors.red, fontSize: 12),
                        ),
                      )
                    else if (_loading)
                      const Padding(
                        padding: EdgeInsets.all(40),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    else if (_events.isEmpty)
                      _InfoGlassCard(
                        title: isPrevious ? 'VORIGE EVENTS' : 'KOMENDE EVENTS',
                        name: isPrevious
                            ? 'Geen vorige events nie'
                            : 'Geen komende events',
                        detail: isPrevious
                            ? 'Voltooide events sal hier verskyn.'
                            : 'Druk “Skep Nuwe Event” om die eerste event te skep.',
                        icon: Icons.event_busy_rounded,
                      )
                    else ...[
                      _SectionTitle(isPrevious ? 'VORIGE EVENTS' : 'KOMENDE EVENTS'),
                      const SizedBox(height: 10),
                      ..._events.map(
                        (event) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: GlassCard(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Icon(
                                      isPrevious
                                          ? Icons.history_rounded
                                          : Icons.event_rounded,
                                      color: kAccent,
                                      size: 28,
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Text(
                                        event.naam,
                                        style: GoogleFonts.inter(
                                          color: kText1,
                                          fontSize: 17,
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 10),
                                Text(
                                  '${event.kampusNaam}${event.lokasieNaam == null ? '' : ' · ${event.lokasieNaam}'}',
                                  style: GoogleFonts.inter(
                                    color: kText2,
                                    fontSize: 12,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${_date(event.beginTyd)} · ${_time(event.beginTyd)}–${_time(event.eindTyd)}',
                                  style: GoogleFonts.inter(
                                    color: kText1,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                const SizedBox(height: 10),
                                Text(
                                  '${event.rsvpAantal} / ${event.kapasiteit} RSVP${isPrevious ? '' : ' · ${event.plekkeOor} plekke oor'}',
                                  style: GoogleFonts.inter(
                                    color: event.vol ? Colors.orange : kTextMuted,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                SizedBox(
                                  width: double.infinity,
                                  child: OutlinedButton.icon(
                                    onPressed: () => _manage(event),
                                    icon: Icon(
                                      isPrevious
                                          ? Icons.analytics_outlined
                                          : Icons.settings_rounded,
                                    ),
                                    label: Text(
                                      isPrevious
                                          ? 'FINALE STATISTIEK'
                                          : 'BESTUUR EVENT',
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
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

class _OpsigterEventFilterButton extends StatelessWidget {
  final String label;
  final bool active;
  final VoidCallback onTap;

  const _OpsigterEventFilterButton({
    required this.label,
    required this.active,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(13),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 11),
          decoration: BoxDecoration(
            color: active ? kAccent.withOpacity(0.14) : const Color(0xFF111827),
            borderRadius: BorderRadius.circular(13),
            border: Border.all(
              color: active ? kAccent.withOpacity(0.65) : const Color(0xFF293548),
            ),
          ),
          child: Text(
            label,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(
              color: active ? kAccent : kTextMuted,
              fontSize: 12,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
      ),
    );
  }
}

class _EventFormPage extends StatefulWidget {
  final MoonEventDto? event;
  const _EventFormPage({this.event});

  @override
  State<_EventFormPage> createState() => _EventFormPageState();
}

class _EventFormPageState extends State<_EventFormPage> {
  final _name = TextEditingController();
  final _capacity = TextEditingController(text: '100');
  final _description = TextEditingController();
  List<KampusDto> _campuses = [];
  List<LokasieDto> _locations = [];
  KampusDto? _campus;
  LokasieDto? _location;
  DateTime _start = DateTime.now().add(const Duration(days: 1));
  DateTime _end = DateTime.now().add(const Duration(days: 1, hours: 2));
  bool _loading = true;
  bool _saving = false;
  String? _error;

  bool get _editing => widget.event != null;

  @override
  void initState() {
    super.initState();
    final e = widget.event;
    if (e != null) {
      _name.text = e.naam;
      _capacity.text = '${e.kapasiteit}';
      _description.text = e.beskrywing ?? '';
      _start = e.beginTyd;
      _end = e.eindTyd;
    }
    _loadLookups();
  }

  @override
  void dispose() {
    _name.dispose();
    _capacity.dispose();
    _description.dispose();
    super.dispose();
  }

  Future<void> _loadLookups() async {
    try {
      final campuses = await MoonApi.fetchOpsigterKampusse();
      final locations = await MoonApi.fetchLokasies();
      if (!mounted) return;
      final targetCampus = widget.event?.kampusId;
      final selectedCampus = campuses.where((c) => c.kampusId == targetCampus).isNotEmpty
          ? campuses.firstWhere((c) => c.kampusId == targetCampus)
          : (campuses.isNotEmpty ? campuses.first : null);
      final targetLocation = widget.event?.lokasieId;
      final selectedLocation = locations.where((l) => l.id == targetLocation).isNotEmpty
          ? locations.firstWhere((l) => l.id == targetLocation)
          : null;
      setState(() {
        _campuses = campuses;
        _locations = locations;
        _campus = selectedCampus;
        _location = selectedLocation;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  List<LokasieDto> get _filteredLocations {
    final id = _campus?.kampusId;
    if (id == null) return [];
    return _locations.where((l) => l.kampusId == id).toList();
  }

  Future<DateTime?> _pickDateTime(DateTime initial) async {
    final date = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime.now().subtract(const Duration(days: 1)),
      lastDate: DateTime.now().add(const Duration(days: 1095)),
      barrierColor: Colors.black.withOpacity(0.88),
      helpText: 'KIES DATUM',
      cancelText: 'KANSELLEER',
      confirmText: 'KIES',
      builder: (context, child) {
        return Theme(
          data: _moonPickerTheme(context),
          child: child!,
        );
      },
    );

    if (date == null || !mounted) return null;

    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initial),
      barrierColor: Colors.black.withOpacity(0.88),
      helpText: 'KIES TYD',
      cancelText: 'KANSELLEER',
      confirmText: 'KIES',
      builder: (context, child) {
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(
            alwaysUse24HourFormat: true,
          ),
          child: Theme(
            data: _moonPickerTheme(context),
            child: child!,
          ),
        );
      },
    );

    if (time == null) return null;

    return DateTime(
      date.year,
      date.month,
      date.day,
      time.hour,
      time.minute,
    );
  }

  String _dt(DateTime value) {
    return '${value.day.toString().padLeft(2, '0')}/${value.month.toString().padLeft(2, '0')}/${value.year}  ${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';
  }

  Future<void> _save() async {
    if (_saving) return;
    final name = _name.text.trim();
    final capacity = int.tryParse(_capacity.text.trim());
    if (name.isEmpty || _campus?.kampusId == null || capacity == null || capacity < 1) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(backgroundColor: Colors.red, content: Text('Vul event naam, kampus en ’n geldige kapasiteit in')));
      return;
    }
    if (!_end.isAfter(_start)) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(backgroundColor: Colors.red, content: Text('Eindtyd moet ná begintyd wees')));
      return;
    }

    setState(() => _saving = true);
    try {
      if (_editing) {
        await MoonApi.updateEvent(
          eventId: widget.event!.eventId,
          naam: name,
          kampusId: _campus!.kampusId!,
          lokasieId: _location?.id,
          beginTyd: _start,
          eindTyd: _end,
          kapasiteit: capacity,
          beskrywing: _description.text,
        );
      } else {
        await MoonApi.createEvent(
          naam: name,
          kampusId: _campus!.kampusId!,
          lokasieId: _location?.id,
          beginTyd: _start,
          eindTyd: _end,
          kapasiteit: capacity,
          beskrywing: _description.text,
        );
      }
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: Colors.red, content: Text(e.toString().replaceFirst('Exception: ', ''))));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(title: _editing ? 'Wysig Event' : 'Skep Event', subtitle: 'Event besonderhede', showBack: true),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : SingleChildScrollView(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          if (_error != null) ...[
                            Text(_error!, style: GoogleFonts.inter(color: Colors.red)),
                            const SizedBox(height: 12),
                          ],
                          _EventField(controller: _name, label: 'Event naam'),
                          const SizedBox(height: 12),
                          GlassCard(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                            child: DropdownButtonHideUnderline(
                              child: DropdownButton<KampusDto>(
                                value: _campus,
                                isExpanded: true,
                                dropdownColor: const Color(0xFF111827),
                                hint: const Text('Kies kampus', style: TextStyle(color: kTextMuted)),
                                items: _campuses.map((c) => DropdownMenuItem(value: c, child: Text(c.naam, style: const TextStyle(color: kText1)))).toList(),
                                onChanged: (value) => setState(() {
                                  _campus = value;
                                  if (_location != null && _location!.kampusId != value?.kampusId) _location = null;
                                }),
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          GlassCard(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                            child: DropdownButtonHideUnderline(
                              child: DropdownButton<LokasieDto>(
                                value: _filteredLocations.any((l) => l.id == _location?.id) ? _location : null,
                                isExpanded: true,
                                dropdownColor: const Color(0xFF111827),
                                hint: const Text('Lokaal / area (opsioneel)', style: TextStyle(color: kTextMuted)),
                                items: _filteredLocations.map((l) => DropdownMenuItem(value: l, child: Text(l.naam, style: const TextStyle(color: kText1)))).toList(),
                                onChanged: (value) => setState(() => _location = value),
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          _DateTimeTile(label: 'Begin', value: _dt(_start), onTap: () async { final v = await _pickDateTime(_start); if (v != null) setState(() => _start = v); }),
                          const SizedBox(height: 10),
                          _DateTimeTile(label: 'Einde', value: _dt(_end), onTap: () async { final v = await _pickDateTime(_end); if (v != null) setState(() => _end = v); }),
                          const SizedBox(height: 12),
                          _EventField(controller: _capacity, label: 'Kapasiteit', keyboardType: TextInputType.number),
                          const SizedBox(height: 12),
                          _EventField(controller: _description, label: 'Beskrywing', maxLines: 4),
                          const SizedBox(height: 18),
                          GradientActionButton(label: _saving ? 'Besig...' : (_editing ? 'Stoor Veranderinge' : 'Skep Event'), onTap: _saving ? () {} : _save, height: 52),
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

class _OpsigterEventDetailPage extends StatefulWidget {
  final MoonEventDto event;
  const _OpsigterEventDetailPage({required this.event});

  @override
  State<_OpsigterEventDetailPage> createState() =>
      _OpsigterEventDetailPageState();
}

class _OpsigterEventDetailPageState
    extends State<_OpsigterEventDetailPage> {
  bool _changed = false;
  bool _sharing = false;
  bool _attendanceLoading = true;
  EventAttendanceDto? _attendance;
  String? _attendanceError;

  @override
  void initState() {
    super.initState();
    _loadAttendance();
  }

  Future<void> _loadAttendance() async {
    try {
      final value = await MoonApi.fetchEventAttendance(widget.event.eventId);
      if (!mounted) return;
      setState(() {
        _attendance = value;
        _attendanceLoading = false;
        _attendanceError = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _attendanceLoading = false;
        _attendanceError = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  String _shareDateTime(DateTime value) {
    final d = value.day.toString().padLeft(2, '0');
    final m = value.month.toString().padLeft(2, '0');
    final h = value.hour.toString().padLeft(2, '0');
    final min = value.minute.toString().padLeft(2, '0');
    return '$d/$m/${value.year} $h:$min';
  }

  Future<void> _shareEvent(BuildContext shareContext) async {
    if (_sharing) return;
    setState(() => _sharing = true);
    try {
      final share = await MoonApi.getEventShareLink(widget.event.eventId);
      if (!mounted) return;
      final e = widget.event;
      final text = [
        'MOON Event',
        e.naam,
        '${_shareDateTime(e.beginTyd)} - ${_shareDateTime(e.eindTyd)}',
        e.kampusNaam,
        if ((e.lokasieNaam ?? '').trim().isNotEmpty) e.lokasieNaam!,
        '',
        'RSVP hier as jy nie die MOON app het nie:',
        share.shareUrl,
      ].join('\n');
      final renderBox = shareContext.findRenderObject() as RenderBox?;
      await SharePlus.instance.share(
        ShareParams(
          text: text,
          subject: 'MOON Event - ${e.naam}',
          sharePositionOrigin: renderBox == null
              ? null
              : renderBox.localToGlobal(Offset.zero) & renderBox.size,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    } finally {
      if (mounted) setState(() => _sharing = false);
    }
  }

  Future<void> _openAttendance() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (_) => _EventLiveAttendancePage(event: widget.event),
      ),
    );
    await _loadAttendance();
  }

  Future<void> _openRsvps() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (_) => _EventRsvpListPage(event: widget.event),
      ),
    );
    await _loadAttendance();
  }

  Future<void> _edit() async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => _EventFormPage(event: widget.event)),
    );
    if (changed == true && mounted) {
      setState(() => _changed = true);
      Navigator.pop(context, true);
    }
  }

  Future<void> _cancel() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF111827),
        title: const Text(
          'Kanselleer Event',
          style: TextStyle(color: Colors.white),
        ),
        content: Text(
          'Kanselleer ${widget.event.naam}?',
          style: const TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Nee'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text(
              'Ja, kanselleer',
              style: TextStyle(color: Colors.red),
            ),
          ),
        ],
      ),
    );
    if (yes != true) return;
    try {
      await MoonApi.cancelEvent(widget.event.eventId);
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
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
    final e = _attendance?.event ?? widget.event;
    final finalStats = _attendance?.finalStats ?? e.eindTyd.isBefore(DateTime.now());
    final a = _attendance;

    String metric(int? value, int fallback) =>
        _attendanceLoading && a == null ? '—' : '${value ?? fallback}';

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: e.naam,
              subtitle: finalStats ? 'Finale Event-statistiek' : 'Event bestuur & live bywoning',
              showBack: true,
            ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: _loadAttendance,
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'RSVP',
                              value: metric(a?.rsvp, e.rsvpAantal),
                              subtitle: 'Bevestig',
                              icon: Icons.how_to_reg_rounded,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'AANGEKOM',
                              value: metric(a?.aangekom, 0),
                              subtitle: 'Minstens een IN',
                              icon: Icons.login_rounded,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'BINNE',
                              value: metric(a?.tansBinne, 0),
                              subtitle: 'Tans in',
                              icon: Icons.groups_rounded,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: _OpsigterMetricCard(
                              label: 'UIT',
                              value: metric(a?.uit, 0),
                              subtitle: 'Reeds uit',
                              icon: Icons.logout_rounded,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      _OpsigterMetricCard(
                        label: finalStats ? 'NO-SHOW' : 'NOG NIE GEKOM',
                        value: metric(
                          finalStats ? a?.noShow : a?.nogNieGekom,
                          e.rsvpAantal,
                        ),
                        subtitle: finalStats
                            ? 'RSVP maar nie opgedaag nie'
                            : 'RSVP wag nog',
                        icon: finalStats
                            ? Icons.person_off_outlined
                            : Icons.schedule_rounded,
                      ),
                      if (_attendanceError != null) ...[
                        const SizedBox(height: 12),
                        Text(
                          _attendanceError!,
                          style: GoogleFonts.inter(color: Colors.red, fontSize: 11),
                        ),
                      ],
                      const SizedBox(height: 14),
                      GlassCard(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              e.kampusNaam,
                              style: GoogleFonts.inter(
                                color: kText1,
                                fontSize: 15,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            if (e.lokasieNaam != null) ...[
                              const SizedBox(height: 4),
                              Text(
                                e.lokasieNaam!,
                                style: GoogleFonts.inter(color: kText2),
                              ),
                            ],
                            const SizedBox(height: 6),
                            Text(
                              '${_shareDateTime(e.beginTyd)} – ${_shareDateTime(e.eindTyd)}',
                              style: GoogleFonts.inter(
                                color: kTextMuted,
                                fontSize: 11,
                              ),
                            ),
                            if ((e.beskrywing ?? '').isNotEmpty) ...[
                              const SizedBox(height: 10),
                              Text(
                                e.beskrywing!,
                                style: GoogleFonts.inter(
                                  color: kTextMuted,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                      const SizedBox(height: 14),
                      GradientActionButton(
                        label: finalStats
                            ? 'FINALE BYWONING & STATISTIEK'
                            : 'LIVE BYWONING',
                        onTap: _openAttendance,
                        height: 52,
                      ),
                      const SizedBox(height: 10),
                      OutlinedButton.icon(
                        onPressed: _openRsvps,
                        icon: const Icon(Icons.people_alt_outlined),
                        label: const Text('RSVP-LYS'),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size.fromHeight(50),
                        ),
                      ),
                      if (!finalStats) ...[
                        const SizedBox(height: 10),
                        Builder(
                          builder: (shareContext) => OutlinedButton.icon(
                            onPressed: _sharing
                                ? null
                                : () => _shareEvent(shareContext),
                            icon: const Icon(Icons.share_rounded, color: kAccent),
                            label: Text(
                              _sharing ? 'Skep deel-skakel...' : 'DEEL EVENT',
                              style: const TextStyle(
                                color: kText1,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            style: OutlinedButton.styleFrom(
                              minimumSize: const Size.fromHeight(52),
                              side: BorderSide(color: kAccent.withOpacity(0.65)),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 10),
                        OutlinedButton.icon(
                          onPressed: _edit,
                          icon: const Icon(Icons.edit_rounded),
                          label: const Text('Wysig Event'),
                        ),
                        const SizedBox(height: 10),
                        OutlinedButton.icon(
                          onPressed: _cancel,
                          icon: const Icon(
                            Icons.cancel_rounded,
                            color: Colors.red,
                          ),
                          label: const Text(
                            'Kanselleer Event',
                            style: TextStyle(color: Colors.red),
                          ),
                        ),
                      ],
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

class _EventLiveAttendancePage extends StatefulWidget {
  final MoonEventDto event;
  const _EventLiveAttendancePage({required this.event});

  @override
  State<_EventLiveAttendancePage> createState() =>
      _EventLiveAttendancePageState();
}

class _EventLiveAttendancePageState
    extends State<_EventLiveAttendancePage> {
  EventAttendanceDto? _data;
  bool _loading = true;
  String? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    if (widget.event.eindTyd.isAfter(DateTime.now())) {
      _timer = Timer.periodic(
        const Duration(seconds: 10),
        (_) => _load(silent: true),
      );
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent && mounted && _data == null) {
      setState(() => _loading = true);
    }
    try {
      final data = await MoonApi.fetchEventAttendance(widget.event.eventId);
      if (!mounted) return;
      setState(() {
        _data = data;
        _loading = false;
        _error = null;
      });
      if (data.finalStats) {
        _timer?.cancel();
        _timer = null;
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  String _time(DateTime? value) {
    if (value == null) return '—';
    return '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}';
  }

  Widget _attendeeCard(EventAttendanceItemDto item) {
    final isIn = item.status == 'IN';
    final isOut = item.status == 'UIT';
    final statusColor = isIn
        ? Colors.green
        : isOut
            ? kAccent
            : kTextMuted;
    final statusText = isIn
        ? 'IN · ${_time(item.laasteAksie)}'
        : isOut
            ? 'UIT · ${_time(item.laasteAksie)}'
            : 'NOG NIE AANGEKOM NIE';

    return GlassCard(
      padding: const EdgeInsets.all(14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: statusColor.withOpacity(0.13),
              borderRadius: BorderRadius.circular(13),
              border: Border.all(color: statusColor.withOpacity(0.45)),
            ),
            child: Icon(
              isIn
                  ? Icons.login_rounded
                  : isOut
                      ? Icons.logout_rounded
                      : Icons.schedule_rounded,
              color: statusColor,
              size: 22,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        item.volleNaam,
                        style: GoogleFonts.inter(
                          color: kText1,
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    if (item.ekstern)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 7,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: kAccent.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(999),
                          border: Border.all(
                            color: kAccent.withOpacity(0.45),
                          ),
                        ),
                        child: Text(
                          'EKSTERN',
                          style: GoogleFonts.inter(
                            color: kAccent,
                            fontSize: 8,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '${item.rol}${item.nommer.isEmpty ? '' : ' · ${item.nommer}'}',
                  style: GoogleFonts.inter(
                    color: kTextMuted,
                    fontSize: 10,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  statusText,
                  style: GoogleFonts.inter(
                    color: statusColor,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                if (item.aangekom && item.eersteIn != null) ...[
                  const SizedBox(height: 3),
                  Text(
                    'Eerste IN: ${_time(item.eersteIn)}',
                    style: GoogleFonts.inter(
                      color: kTextMuted,
                      fontSize: 9,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final data = _data;
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: data?.finalStats == true
                  ? 'Finale Bywoning'
                  : 'Live Bywoning',
              subtitle: widget.event.naam,
              showBack: true,
            ),
            Expanded(
              child: _loading && data == null
                  ? const Center(child: CircularProgressIndicator())
                  : RefreshIndicator(
                      onRefresh: () => _load(),
                      child: ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.all(16),
                        children: [
                          if (_error != null) ...[
                            Text(
                              _error!,
                              style: GoogleFonts.inter(
                                color: Colors.red,
                                fontSize: 11,
                              ),
                            ),
                            const SizedBox(height: 12),
                          ],
                          if (data != null) ...[
                            Row(
                              children: [
                                Expanded(
                                  child: _OpsigterMetricCard(
                                    label: 'RSVP',
                                    value: '${data.rsvp}',
                                    subtitle: '${data.appRsvp} app · ${data.eksterneRsvp} ekstern',
                                    icon: Icons.how_to_reg_rounded,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: _OpsigterMetricCard(
                                    label: 'AANGEKOM',
                                    value: '${data.aangekom}',
                                    subtitle: 'Unieke persone',
                                    icon: Icons.login_rounded,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                Expanded(
                                  child: _OpsigterMetricCard(
                                    label: 'BINNE',
                                    value: '${data.tansBinne}',
                                    subtitle: 'Tans in',
                                    icon: Icons.groups_rounded,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: _OpsigterMetricCard(
                                    label: 'UIT',
                                    value: '${data.uit}',
                                    subtitle: 'Reeds uit',
                                    icon: Icons.logout_rounded,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            _OpsigterMetricCard(
                              label: data.finalStats ? 'NO-SHOW' : 'NOG NIE',
                              value: data.finalStats
                                  ? '${data.noShow}'
                                  : '${data.nogNieGekom}',
                              subtitle: data.finalStats
                                  ? 'RSVP maar nie opgedaag nie'
                                  : 'Nog nie aangekom nie',
                              icon: data.finalStats
                                  ? Icons.person_off_outlined
                                  : Icons.schedule_rounded,
                            ),
                            if (data.finalStats) ...[
                              const SizedBox(height: 12),
                              GlassCard(
                                padding: const EdgeInsets.all(14),
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        'IN skanderings\n${data.inSkanderings}',
                                        textAlign: TextAlign.center,
                                        style: GoogleFonts.inter(
                                          color: kText1,
                                          fontSize: 13,
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 10),
                                    Expanded(
                                      child: Text(
                                        'UIT skanderings\n${data.uitSkanderings}',
                                        textAlign: TextAlign.center,
                                        style: GoogleFonts.inter(
                                          color: kText1,
                                          fontSize: 13,
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                            const SizedBox(height: 18),
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    data.finalStats
                                        ? 'FINALE BYWONING'
                                        : 'LIVE BYWONING',
                                    style: GoogleFonts.inter(
                                      color: kTextMuted,
                                      fontSize: 9,
                                      fontWeight: FontWeight.w900,
                                      letterSpacing: 1.1,
                                    ),
                                  ),
                                ),
                                if (!data.finalStats)
                                  Text(
                                    'Outo-herlaai: 10s',
                                    style: GoogleFonts.inter(
                                      color: kTextMuted,
                                      fontSize: 9,
                                    ),
                                  ),
                              ],
                            ),
                            const SizedBox(height: 9),
                            if (data.attendees.isEmpty)
                              GlassCard(
                                padding: const EdgeInsets.all(20),
                                child: Text(
                                  'Nog geen RSVP’s vir hierdie event nie.',
                                  textAlign: TextAlign.center,
                                  style: GoogleFonts.inter(
                                    color: kTextMuted,
                                    fontSize: 12,
                                  ),
                                ),
                              )
                            else
                              ...data.attendees.map(
                                (item) => Padding(
                                  padding: const EdgeInsets.only(bottom: 8),
                                  child: _attendeeCard(item),
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

class _EventRsvpListPage extends StatefulWidget {
  final MoonEventDto event;
  const _EventRsvpListPage({required this.event});

  @override
  State<_EventRsvpListPage> createState() => _EventRsvpListPageState();
}

class _EventRsvpListPageState extends State<_EventRsvpListPage> {
  bool _loading = true;
  String? _error;
  int? _busyExternalId;
  List<EventRsvpItemDto> _items = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final items = await MoonApi.fetchEventRsvps(widget.event.eventId);
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _loading = false;
      });
    }
  }

  Future<void> _cancelExternal(EventRsvpItemDto item) async {
    final id = item.publiekRsvpId;
    if (id == null || _busyExternalId != null) return;
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF111827),
        title: const Text(
          'Kanselleer eksterne RSVP',
          style: TextStyle(color: Colors.white),
        ),
        content: Text(
          'Kanselleer ${item.volleNaam} se RSVP? Die persoon se Event QR sal onmiddellik ongeldig wees.',
          style: const TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Nee'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text(
              'JA, KANSELLEER',
              style: TextStyle(color: Colors.red),
            ),
          ),
        ],
      ),
    );
    if (yes != true) return;

    setState(() => _busyExternalId = id);
    try {
      await MoonApi.cancelExternalEventRsvp(
        eventId: widget.event.eventId,
        publiekRsvpId: id,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Eksterne RSVP gekanselleer; QR is nou ongeldig.')),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(e.toString().replaceFirst('Exception: ', '')),
        ),
      );
    } finally {
      if (mounted) setState(() => _busyExternalId = null);
    }
  }

  Widget _rsvpCard(EventRsvpItemDto item) {
    final busy = item.publiekRsvpId != null &&
        _busyExternalId == item.publiekRsvpId;
    return GlassCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                item.ekstern
                    ? Icons.public_rounded
                    : Icons.check_circle_rounded,
                color: item.ekstern ? kAccent : Colors.green,
                size: 26,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            item.volleNaam,
                            style: GoogleFonts.inter(
                              color: kText1,
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        if (item.ekstern)
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 7,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: kAccent.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(999),
                              border: Border.all(
                                color: kAccent.withOpacity(0.45),
                              ),
                            ),
                            child: Text(
                              'EKSTERN',
                              style: GoogleFonts.inter(
                                color: kAccent,
                                fontSize: 8,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${item.rol}${item.nommer.isEmpty ? '' : ' · ${item.nommer}'}',
                      style: GoogleFonts.inter(
                        color: kTextMuted,
                        fontSize: 11,
                      ),
                    ),
                    if (item.ekstern &&
                        (item.epos ?? '').trim().isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(
                        item.epos!,
                        style: GoogleFonts.inter(
                          color: kText2,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
          if (item.ekstern && item.publiekRsvpId != null) ...[
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: busy ? null : () => _cancelExternal(item),
              icon: const Icon(Icons.cancel_outlined, color: Colors.red),
              label: Text(
                busy ? 'KANSELLEER...' : 'KANSELLEER RSVP',
                style: const TextStyle(color: Colors.red),
              ),
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final appItems = _items.where((item) => !item.ekstern).toList();
    final externalItems = _items.where((item) => item.ekstern).toList();

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'RSVP-Lys',
              subtitle: widget.event.naam,
              showBack: true,
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Text(
                            _error!,
                            style: const TextStyle(color: Colors.red),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _load,
                          child: ListView(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.all(16),
                            children: [
                              if (_items.isEmpty) ...[
                                const SizedBox(height: 80),
                                const Icon(
                                  Icons.event_busy_rounded,
                                  color: kTextMuted,
                                  size: 48,
                                ),
                                const SizedBox(height: 12),
                                Text(
                                  "Nog geen RSVP's nie",
                                  textAlign: TextAlign.center,
                                  style: GoogleFonts.inter(
                                    color: kTextMuted,
                                    fontSize: 13,
                                  ),
                                ),
                              ] else ...[
                                Text(
                                  "APP RSVP'S  ·  ${appItems.length}",
                                  style: GoogleFonts.inter(
                                    color: kTextMuted,
                                    fontSize: 9,
                                    fontWeight: FontWeight.w900,
                                    letterSpacing: 1.0,
                                  ),
                                ),
                                const SizedBox(height: 9),
                                if (appItems.isEmpty)
                                  Text(
                                    "Geen app RSVP's nie",
                                    style: GoogleFonts.inter(
                                      color: kTextMuted,
                                      fontSize: 11,
                                    ),
                                  )
                                else
                                  ...appItems.map(
                                    (item) => Padding(
                                      padding: const EdgeInsets.only(bottom: 8),
                                      child: _rsvpCard(item),
                                    ),
                                  ),
                                const SizedBox(height: 18),
                                Text(
                                  'EKSTERNE GASTE  ·  ${externalItems.length}',
                                  style: GoogleFonts.inter(
                                    color: kTextMuted,
                                    fontSize: 9,
                                    fontWeight: FontWeight.w900,
                                    letterSpacing: 1.0,
                                  ),
                                ),
                                const SizedBox(height: 9),
                                if (externalItems.isEmpty)
                                  Text(
                                    "Nog geen eksterne RSVP's via die deel-skakel nie",
                                    style: GoogleFonts.inter(
                                      color: kTextMuted,
                                      fontSize: 11,
                                    ),
                                  )
                                else
                                  ...externalItems.map(
                                    (item) => Padding(
                                      padding: const EdgeInsets.only(bottom: 8),
                                      child: _rsvpCard(item),
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

class _EventField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final int maxLines;
  final TextInputType? keyboardType;
  const _EventField({required this.controller, required this.label, this.maxLines = 1, this.keyboardType});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      child: TextField(
        controller: controller,
        maxLines: maxLines,
        keyboardType: keyboardType,
        style: GoogleFonts.inter(color: kText1),
        decoration: InputDecoration(border: InputBorder.none, labelText: label, labelStyle: GoogleFonts.inter(color: kTextMuted)),
      ),
    );
  }
}

class _DateTimeTile extends StatelessWidget {
  final String label;
  final String value;
  final VoidCallback onTap;
  const _DateTimeTile({required this.label, required this.value, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: GlassCard(
          padding: const EdgeInsets.all(14),
          child: Row(children: [
            const Icon(Icons.schedule_rounded, color: kAccent),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(label, style: GoogleFonts.inter(color: kTextMuted, fontSize: 10, fontWeight: FontWeight.w700)),
              const SizedBox(height: 3),
              Text(value, style: GoogleFonts.inter(color: kText1, fontSize: 13, fontWeight: FontWeight.w600)),
            ])),
            const Icon(Icons.chevron_right_rounded, color: kTextMuted),
          ]),
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
  final VoidCallback? onTap;

  const _OpsigterMetricCard({
    required this.label,
    required this.value,
    required this.subtitle,
    required this.icon,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final card = GlassCard(
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

    if (onTap == null) return card;

    return Semantics(
      button: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: card,
      ),
    );
  }
}


class _OpsigterQuickActionCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String subtitle;
  final VoidCallback onTap;
  final bool danger;

  const _OpsigterQuickActionCard({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.onTap,
    this.danger = false,
  });

  @override
  Widget build(BuildContext context) {
    final accent = danger ? Colors.red : kAccent;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          height: 112,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: danger
                ? Colors.red.withOpacity(0.08)
                : const Color(0x0DFFFFFF),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: danger
                  ? Colors.red.withOpacity(0.45)
                  : const Color(0x14FFFFFF),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: accent, size: 28),
              const Spacer(),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: GoogleFonts.inter(
                  color: kText1,
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                subtitle,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: GoogleFonts.inter(
                  color: kTextMuted,
                  fontSize: 10,
                ),
              ),
            ],
          ),
        ),
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
      _NavItem(icon: Icons.dashboard_rounded, label: 'Dashboard'),
      _NavItem(icon: Icons.location_city_rounded, label: 'Kampus'),
      _NavItem(icon: Icons.apartment_rounded, label: 'Koshuis'),
      _NavItem(icon: Icons.emergency_rounded, label: 'Nood'),
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
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Text(
                      items[i].label,
                      maxLines: 1,
                      style: GoogleFonts.inter(
                        color: active ? kText1 : kTextMuted,
                        fontSize: 9.5,
                        fontWeight: active
                            ? FontWeight.w600
                            : FontWeight.w400,
                      ),
                    ),
                  ),
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
