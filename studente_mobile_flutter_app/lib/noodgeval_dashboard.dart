import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;

import 'app_shared.dart';
import 'moon_api.dart';

/// Step 9: Opsigter se live noodbeheer + noodkontrole-skerm.
///
/// Belangrik:
/// - Die WebSocket is slegs oop terwyl daar 'n AKTIEWE noodgeval is.
/// - Wanneer daar geen noodgeval is nie, doen die oop skerm net 'n ligte REST-check
///   elke 5 sekondes. MQTT bly die permanente noodkanaal buite hierdie skerm.
/// - DAAR / NIE DAAR NIE is opsigter-kontrole en bly apart van
///   ONTVANG / KENNIS_GENEEM.
class NoodgevalDashboardPage extends StatefulWidget {
  const NoodgevalDashboardPage({super.key});

  @override
  State<NoodgevalDashboardPage> createState() =>
      _NoodgevalDashboardPageState();
}

class _NoodgevalDashboardPageState extends State<NoodgevalDashboardPage> {
  final TextEditingController _searchController = TextEditingController();

  List<KampusDto> _campuses = [];
  KampusDto? _campus;
  Map<String, dynamic>? _snapshot;

  WebSocket? _socket;
  StreamSubscription<dynamic>? _socketSubscription;
  Timer? _idlePollTimer;
  Timer? _reconnectTimer;

  bool _loadingCampuses = true;
  bool _checkingEmergency = false;
  bool _socketConnected = false;
  bool _emergencyActionBusy = false;
  bool _disposed = false;
  String? _error;
  String _query = '';
  int? _activeEmergencyId;
  final Set<int> _busyUsers = <int>{};

  @override
  void initState() {
    super.initState();
    _searchController.addListener(() {
      if (!mounted) return;
      setState(() => _query = _searchController.text.trim().toLowerCase());
    });
    _loadCampuses();
  }

  @override
  void dispose() {
    _disposed = true;
    _idlePollTimer?.cancel();
    _reconnectTimer?.cancel();
    _socketSubscription?.cancel();
    _socket?.close();
    _searchController.dispose();
    super.dispose();
  }

  Map<String, String> get _authHeaders => <String, String>{
        'Accept': 'application/json',
        if ((MoonApi.bearerToken ?? '').trim().isNotEmpty)
          'Authorization': 'Bearer ${MoonApi.bearerToken!.trim()}',
      };

  Future<void> _loadCampuses() async {
    try {
      final campuses = await MoonApi.fetchOpsigterKampusse();
      if (!mounted) return;

      final usable = campuses.where((c) => c.kampusId != null).toList();
      setState(() {
        _campuses = usable;
        _campus = usable.isNotEmpty ? usable.first : null;
        _loadingCampuses = false;
        _error = usable.isEmpty ? 'Geen kampus is aan hierdie gebruiker gekoppel nie.' : null;
      });

      if (_campus?.kampusId != null) {
        // Hou die kampus-WebSocket permanent oop terwyl hierdie Nood-skerm oop is.
        // Dit laat meer as een Opsigter op dieselfde kampus onmiddellik dieselfde
        // noodgeval-toestand sien, selfs voordat 'n noodgeval geaktiveer is.
        await _connectSocket();
        if (!_socketConnected) {
          await _checkActiveEmergency(force: true);
        }
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingCampuses = false;
        _error = _cleanError(e);
      });
    }
  }

  Future<void> _selectCampus(KampusDto? campus) async {
    if (campus?.kampusId == null || campus?.kampusId == _campus?.kampusId) return;
    await _disconnectSocket();
    _idlePollTimer?.cancel();
    _reconnectTimer?.cancel();

    if (!mounted) return;
    setState(() {
      _campus = campus;
      _snapshot = null;
      _activeEmergencyId = null;
      _error = null;
    });
    await _connectSocket();
    if (!_socketConnected) {
      await _checkActiveEmergency(force: true);
    }
  }

  Future<void> _checkActiveEmergency({bool force = false}) async {
    final campusId = _campus?.kampusId;
    if (campusId == null || _checkingEmergency) return;
    if (_activeEmergencyId != null && !force) return;

    if (mounted) setState(() => _checkingEmergency = true);

    try {
      final uri = Uri.parse('${MoonApi.baseUrl}/noodgeval/aktief')
          .replace(queryParameters: {'kampus_id': '$campusId'});
      final response = await http.get(uri, headers: _authHeaders);
      final decoded = _decodeApi(response, fallback: 'Kon nie aktiewe noodgeval nagaan nie.');
      final raw = decoded['data'];
      final rows = raw is List ? raw : const [];

      if (rows.isEmpty) {
        if (!mounted) return;
        setState(() {
          _activeEmergencyId = null;
          _snapshot = null;
          _error = null;
        });
        // Moenie 'n werkende socket ontkoppel net omdat daar nog geen nood is nie.
        // Die oop socket is presies wat 'n tweede Opsigter se skerm onmiddellik
        // laat reageer wanneer 'n ander Opsigter 'n nood aktiveer.
        if (_socketConnected) {
          _idlePollTimer?.cancel();
        } else {
          _startIdlePolling();
        }
      } else {
        final first = Map<String, dynamic>.from(rows.first as Map);
        final id = _readInt(first, const ['Noodgeval_ID', 'noodgeval_id']);
        if (id == null) {
          throw Exception('Aktiewe noodgeval het nie ’n geldige ID nie.');
        }
        _idlePollTimer?.cancel();
        if (!mounted) return;
        setState(() {
          _activeEmergencyId = id;
          _error = null;
        });
        await _connectSocket();
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = _cleanError(e));
      if (_activeEmergencyId == null) _startIdlePolling();
    } finally {
      if (mounted) setState(() => _checkingEmergency = false);
    }
  }

  void _startIdlePolling() {
    // REST polling is nou slegs 'n fallback indien die WebSocket nie beskikbaar is nie.
    if (_disposed || _socketConnected || _campus?.kampusId == null) return;
    _idlePollTimer?.cancel();
    _idlePollTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!_disposed && !_socketConnected && _campus?.kampusId != null) {
        _checkActiveEmergency(force: true);
      }
    });
  }

  Uri _webSocketUri(int campusId) {
    final base = Uri.parse(MoonApi.baseUrl);
    final token = (MoonApi.bearerToken ?? '').trim();
    final scheme = base.scheme == 'https' ? 'wss' : 'ws';
    final basePath = base.path == '/' ? '' : base.path.replaceFirst(RegExp(r'/$'), '');
    return base.replace(
      scheme: scheme,
      path: '$basePath/noodgeval/ws/kampus/$campusId',
      queryParameters: {'token': token},
    );
  }

  Future<void> _connectSocket() async {
    final campusId = _campus?.kampusId;
    // Die socket bly oop vir die gekose kampus, selfs wanneer daar nog geen
    // aktiewe noodgeval is nie. Dit is die kern van multi-Opsigter live sync.
    if (campusId == null || _disposed) return;
    if (_socketConnected || _socket != null) return;

    final token = (MoonApi.bearerToken ?? '').trim();
    if (token.isEmpty) {
      if (mounted) setState(() => _error = 'Geen geldige login-token beskikbaar nie.');
      return;
    }

    _reconnectTimer?.cancel();
    try {
      final socket = await WebSocket.connect(_webSocketUri(campusId).toString());
      if (_disposed || _campus?.kampusId != campusId) {
        await socket.close();
        return;
      }

      _socket = socket;
      _idlePollTimer?.cancel();
      if (mounted) {
        setState(() {
          _socketConnected = true;
          _error = null;
        });
      }

      _socketSubscription = socket.listen(
        _handleSocketMessage,
        onError: (Object e) => _handleSocketClosed(error: e),
        onDone: () => _handleSocketClosed(),
        cancelOnError: false,
      );
    } catch (e) {
      _socket = null;
      if (mounted) {
        setState(() {
          _socketConnected = false;
          _error = 'Live verbinding kon nie koppel nie: ${_cleanError(e)}';
        });
      }
      _startIdlePolling();
      _scheduleReconnect();
    }
  }

  void _handleSocketMessage(dynamic raw) {
    try {
      final dynamic decoded = jsonDecode(raw.toString());
      if (decoded is! Map) return;
      final snapshot = Map<String, dynamic>.from(decoded);

      if (snapshot['tipe'] == 'FOUT') {
        if (mounted) setState(() => _error = snapshot['fout']?.toString());
        return;
      }

      final active = snapshot['aktiewe_noodgeval'];
      if (active == null) {
        if (mounted) {
          setState(() {
            _snapshot = null;
            _activeEmergencyId = null;
            _busyUsers.clear();
            _error = null;
          });
        }
        // Bly gekoppel. As 'n ander Opsigter op dieselfde kampus nou 'n nood
        // aktiveer, stuur die backend binne ongeveer 1 sekonde die nuwe snapshot.
        _idlePollTimer?.cancel();
        return;
      }

      final activeMap = Map<String, dynamic>.from(active as Map);
      final emergencyId = _readInt(activeMap, const ['noodgeval_id', 'Noodgeval_ID']);
      if (!mounted) return;
      setState(() {
        _snapshot = snapshot;
        _activeEmergencyId = emergencyId ?? _activeEmergencyId;
        _error = null;
        _busyUsers.clear();
      });
    } catch (e) {
      if (mounted) setState(() => _error = 'Live data kon nie gelees word nie: ${_cleanError(e)}');
    }
  }

  Future<void> _disconnectSocket() async {
    _reconnectTimer?.cancel();
    final sub = _socketSubscription;
    final socket = _socket;
    _socketSubscription = null;
    _socket = null;
    if (mounted) setState(() => _socketConnected = false);
    try {
      await sub?.cancel();
    } catch (_) {}
    try {
      await socket?.close();
    } catch (_) {}
  }

  void _handleSocketClosed({Object? error}) {
    _socketSubscription = null;
    _socket = null;
    if (mounted) {
      setState(() {
        _socketConnected = false;
        if (error != null) _error = 'Live verbinding onderbreek: ${_cleanError(error)}';
      });
    }
    // Probeer altyd die kampus-socket herstel, ongeag of daar tans 'n aktiewe
    // noodgeval is. REST bly intussen die fallback.
    _startIdlePolling();
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_disposed || _campus?.kampusId == null) return;
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 2), () {
      if (!_disposed && !_socketConnected && _campus?.kampusId != null) {
        _connectSocket();
      }
    });
  }

  Future<Map<String, String>?> _showActivateDialog() async {
    final titleController = TextEditingController(text: 'KAMPUS NOODGEVAL');
    final messageController = TextEditingController(
      text: 'Noodgeval op ${_campus?.naam ?? 'die kampus'}. Neem asseblief kennis en volg die noodinstruksies.',
    );

    try {
      return await showDialog<Map<String, String>>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) {
          return AlertDialog(
            backgroundColor: const Color(0xFF0F172A),
            title: Row(
              children: [
                const Icon(Icons.emergency_rounded, color: Colors.red),
                const SizedBox(width: 9),
                Expanded(
                  child: Text(
                    'Aktiveer noodgeval',
                    style: GoogleFonts.inter(color: kText1, fontWeight: FontWeight.w900),
                  ),
                ),
              ],
            ),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Hierdie aksie stuur onmiddellik die MQTT-noodsein na ${_campus?.naam ?? 'die kampus'}.',
                    style: GoogleFonts.inter(color: Colors.red.shade200, fontSize: 11, height: 1.4),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: titleController,
                    maxLength: 150,
                    style: GoogleFonts.inter(color: kText1),
                    decoration: const InputDecoration(
                      labelText: 'Titel',
                      hintText: 'KAMPUS NOODGEVAL',
                    ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: messageController,
                    minLines: 3,
                    maxLines: 6,
                    maxLength: 2000,
                    style: GoogleFonts.inter(color: kText1),
                    decoration: const InputDecoration(
                      labelText: 'Boodskap',
                      hintText: 'Wat moet gebruikers weet?',
                      alignLabelWithHint: true,
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: const Text('KANSELLEER'),
              ),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: Colors.red.shade700),
                onPressed: () {
                  final title = titleController.text.trim();
                  final message = messageController.text.trim();
                  if (title.isEmpty || message.isEmpty) {
                    ScaffoldMessenger.of(dialogContext).showSnackBar(
                      const SnackBar(
                        backgroundColor: Color(0xFFB91C1C),
                        behavior: SnackBarBehavior.floating,
                        content: Text(
                          'Titel en boodskap is verpligtend.',
                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
                        ),
                      ),
                    );
                    return;
                  }
                  Navigator.pop(dialogContext, <String, String>{
                    'titel': title,
                    'boodskap': message,
                  });
                },
                icon: const Icon(Icons.warning_amber_rounded),
                label: const Text('STUUR NOODSEIN'),
              ),
            ],
          );
        },
      );
    } finally {
      titleController.dispose();
      messageController.dispose();
    }
  }

  Future<void> _activateEmergency() async {
    final campusId = _campus?.kampusId;
    if (campusId == null || _emergencyActionBusy) return;

    final details = await _showActivateDialog();
    if (details == null || !mounted) return;

    setState(() {
      _emergencyActionBusy = true;
      _error = null;
    });
    _idlePollTimer?.cancel();

    try {
      final response = await http.post(
        Uri.parse('${MoonApi.baseUrl}/noodgeval'),
        headers: <String, String>{
          ..._authHeaders,
          'Content-Type': 'application/json',
        },
        body: jsonEncode(<String, dynamic>{
          'kampus_id': campusId,
          'tipe': 'NOODGEVAL',
          'titel': details['titel'],
          'boodskap': details['boodskap'],
        }),
      );
      final decoded = _decodeApi(response, fallback: 'Noodgeval kon nie geaktiveer word nie.');
      final dataRaw = decoded['data'];
      final data = dataRaw is Map ? Map<String, dynamic>.from(dataRaw) : <String, dynamic>{};
      final emergencyRaw = data['noodgeval'];
      final emergency = emergencyRaw is Map
          ? Map<String, dynamic>.from(emergencyRaw)
          : <String, dynamic>{};
      final id = _readInt(emergency, const ['Noodgeval_ID', 'noodgeval_id']);

      if (!mounted) return;
      setState(() {
        _activeEmergencyId = id;
        _snapshot = null;
        _error = null;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Color(0xFFB91C1C),
          behavior: SnackBarBehavior.floating,
          content: Text(
            'Noodgeval geaktiveer — MQTT-noodsein is gestuur.',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
          ),
        ),
      );
      await _checkActiveEmergency(force: true);
    } catch (e) {
      // Indien die DB-skep suksesvol was maar MQTT gefaal het, kan die API 503 gee.
      // Kontroleer daarom die gesaghebbende DB-status voordat ons terugkeer idle toe.
      await _checkActiveEmergency(force: true);
      if (!mounted) return;
      setState(() => _error = _cleanError(e));
      _showError(_cleanError(e));
    } finally {
      if (mounted) setState(() => _emergencyActionBusy = false);
    }
  }

  Future<bool> _confirmCloseEmergency() async {
    return await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (dialogContext) => AlertDialog(
            backgroundColor: const Color(0xFF0F172A),
            title: Text(
              'Sluit noodgeval?',
              style: GoogleFonts.inter(color: kText1, fontWeight: FontWeight.w900),
            ),
            content: Text(
              'Hierdie aksie stuur die GESLUIT MQTT-boodskap. Die noodalarm op toestelle moet dan stop. Sluit slegs wanneer die noodgeval werklik verby is.',
              style: GoogleFonts.inter(color: kText2, fontSize: 12, height: 1.45),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const Text('KANSELLEER'),
              ),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: Colors.green.shade700),
                onPressed: () => Navigator.pop(dialogContext, true),
                icon: const Icon(Icons.check_circle_outline_rounded),
                label: const Text('JA, SLUIT NOOD'),
              ),
            ],
          ),
        ) ??
        false;
  }

  Future<void> _closeEmergency() async {
    final emergencyId = _activeEmergencyId;
    if (emergencyId == null || _emergencyActionBusy) return;
    if (!await _confirmCloseEmergency() || !mounted) return;

    setState(() {
      _emergencyActionBusy = true;
      _error = null;
    });

    try {
      final response = await http.post(
        Uri.parse('${MoonApi.baseUrl}/noodgeval/$emergencyId/sluit'),
        headers: _authHeaders,
      );
      _decodeApi(response, fallback: 'Noodgeval kon nie gesluit word nie.');

      if (!mounted) return;
      setState(() {
        _activeEmergencyId = null;
        _snapshot = null;
        _busyUsers.clear();
        _error = null;
      });
      // Hou die kampus-WebSocket oop. Die ander Opsigters kry dieselfde
      // GESLUIT toestand uit PostgreSQL, en hierdie toestel bly gereed vir die
      // volgende noodgeval sonder 'n handmatige refresh.
      if (!_socketConnected) {
        _startIdlePolling();
        _scheduleReconnect();
      }

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Color(0xFF15803D),
          behavior: SnackBarBehavior.floating,
          content: Text(
            'Noodgeval gesluit — MQTT-stopsein is gestuur.',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
          ),
        ),
      );
    } catch (e) {
      // Sluit kan reeds in die DB gebeur het voordat 'n MQTT-fout terugkom.
      await _checkActiveEmergency(force: true);
      if (!mounted) return;
      setState(() => _error = _cleanError(e));
      _showError(_cleanError(e));
    } finally {
      if (mounted) setState(() => _emergencyActionBusy = false);
    }
  }

  Future<void> _resendEmergency() async {
    final emergencyId = _activeEmergencyId;
    if (emergencyId == null || _emergencyActionBusy) return;

    setState(() => _emergencyActionBusy = true);
    try {
      final response = await http.post(
        Uri.parse('${MoonApi.baseUrl}/noodgeval/$emergencyId/herstuur'),
        headers: _authHeaders,
      );
      _decodeApi(response, fallback: 'Noodsein kon nie herstuur word nie.');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Color(0xFF2563EB),
          behavior: SnackBarBehavior.floating,
          content: Text(
            'Noodsein weer via MQTT gestuur.',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      _showError(_cleanError(e));
    } finally {
      if (mounted) setState(() => _emergencyActionBusy = false);
    }
  }

  int? _personBusyKey(Map<String, dynamic> person) {
    final gebruikerId = _readInt(person, const ['gebruiker_id']);
    if (gebruikerId != null) return gebruikerId;
    final publiekRsvpId = _readInt(person, const ['publiek_rsvp_id']);
    if (publiekRsvpId != null) return -publiekRsvpId;
    return null;
  }

  Future<void> _markPerson(Map<String, dynamic> person, String status) async {
    final emergencyId = _activeEmergencyId;
    final gebruikerId = _readInt(person, const ['gebruiker_id']);
    final publiekRsvpId = _readInt(person, const ['publiek_rsvp_id']);
    final busyKey = _personBusyKey(person);
    if (emergencyId == null || busyKey == null || _busyUsers.contains(busyKey)) return;

    setState(() => _busyUsers.add(busyKey));
    final action = status == 'DAAR' ? 'daar' : 'nie-daar';

    try {
      final String path;
      if (publiekRsvpId != null) {
        path = '/noodgeval/$emergencyId/event-gas/$publiekRsvpId/kontrole/$action';
      } else if (gebruikerId != null) {
        path = '/noodgeval/$emergencyId/kontrole/$gebruikerId/$action';
      } else {
        throw Exception('Persoon het geen geldige noodkontrole-ID nie.');
      }

      final response = await http.post(
        Uri.parse('${MoonApi.baseUrl}$path'),
        headers: _authHeaders,
      );
      _decodeApi(response, fallback: 'Persoon kon nie gemerk word nie.');
      // WebSocket stuur binne ongeveer 1 sekonde die gesaghebbende nuwe lys.
    } catch (e) {
      if (!mounted) return;
      setState(() => _busyUsers.remove(busyKey));
      _showError(_cleanError(e));
    }
  }

  Future<void> _restorePerson(Map<String, dynamic> person) async {
    final emergencyId = _activeEmergencyId;
    final gebruikerId = _readInt(person, const ['gebruiker_id']);
    final publiekRsvpId = _readInt(person, const ['publiek_rsvp_id']);
    final busyKey = _personBusyKey(person);
    if (emergencyId == null || busyKey == null || _busyUsers.contains(busyKey)) return;

    setState(() => _busyUsers.add(busyKey));
    try {
      final String path;
      if (publiekRsvpId != null) {
        path = '/noodgeval/$emergencyId/event-gas/$publiekRsvpId/kontrole/herstel';
      } else if (gebruikerId != null) {
        path = '/noodgeval/$emergencyId/kontrole/$gebruikerId/herstel';
      } else {
        throw Exception('Persoon het geen geldige noodkontrole-ID nie.');
      }

      final response = await http.post(
        Uri.parse('${MoonApi.baseUrl}$path'),
        headers: _authHeaders,
      );
      _decodeApi(response, fallback: 'Persoon kon nie herstel word nie.');
    } catch (e) {
      if (!mounted) return;
      setState(() => _busyUsers.remove(busyKey));
      _showError(_cleanError(e));
    }
  }

  Map<String, dynamic> _decodeApi(http.Response response, {required String fallback}) {
    dynamic decoded;
    try {
      decoded = jsonDecode(response.body);
    } catch (_) {
      throw Exception('$fallback HTTP ${response.statusCode}');
    }
    if (decoded is! Map) throw Exception(fallback);
    final map = Map<String, dynamic>.from(decoded);
    if (response.statusCode < 200 || response.statusCode >= 300 || map['sukses'] != true) {
      final message = map['fout'] ?? map['detail'] ?? fallback;
      throw Exception(message.toString());
    }
    return map;
  }

  int? _readInt(Map<String, dynamic> map, List<String> keys) {
    for (final key in keys) {
      final value = map[key];
      if (value is int) return value;
      if (value is num) return value.toInt();
      final parsed = int.tryParse(value?.toString() ?? '');
      if (parsed != null) return parsed;
    }
    return null;
  }

  String _cleanError(Object error) => error.toString().replaceFirst('Exception: ', '');

  void _showError(String text) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: Colors.red.shade700,
        behavior: SnackBarBehavior.floating,
        content: Text(
          text,
          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
        ),
      ),
    );
  }

  Map<String, dynamic> get _stats {
    final raw = _snapshot?['stats'];
    return raw is Map ? Map<String, dynamic>.from(raw) : <String, dynamic>{};
  }

  List<Map<String, dynamic>> _listFromSnapshot(String key) {
    final raw = _snapshot?[key];
    if (raw is! List) return [];
    return raw
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  bool _matches(Map<String, dynamic> person) {
    if (_query.isEmpty) return true;
    final haystack = <String>[
      person['volle_naam']?.toString() ?? '',
      person['naam']?.toString() ?? '',
      person['van']?.toString() ?? '',
      person['nommer']?.toString() ?? '',
      person['tipe']?.toString() ?? '',
      person['event_name']?.toString() ?? '',
      person['event_gas_tipe']?.toString() ?? '',
    ].join(' ').toLowerCase();
    return haystack.contains(_query);
  }

  String? _photoUrl(Map<String, dynamic> person) {
    final raw = person['foto_url']?.toString().trim() ?? '';
    if (raw.isEmpty) return null;
    final parsed = Uri.tryParse(raw);
    if (parsed != null && parsed.hasScheme) return raw;
    final base = MoonApi.baseUrl.replaceFirst(RegExp(r'/$'), '');
    final path = raw.replaceFirst(RegExp(r'^/'), '');
    return '$base/$path';
  }

  void _showPhoto(Map<String, dynamic> person) {
    final url = _photoUrl(person);
    if (url == null) return;
    showDialog<void>(
      context: context,
      builder: (_) => Dialog(
        backgroundColor: const Color(0xFF0F172A),
        insetPadding: const EdgeInsets.all(24),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: Image.network(
                  url,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const SizedBox(
                    height: 280,
                    child: Center(child: Icon(Icons.person, color: kTextMuted, size: 80)),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Text(
                person['volle_naam']?.toString() ?? '',
                style: GoogleFonts.inter(color: kText1, fontWeight: FontWeight.w800),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _avatar(Map<String, dynamic> person) {
    final url = _photoUrl(person);
    final initials = '${person['naam']?.toString().isNotEmpty == true ? person['naam'].toString()[0] : ''}'
        '${person['van']?.toString().isNotEmpty == true ? person['van'].toString()[0] : ''}'
        .toUpperCase();

    return GestureDetector(
      onTap: url == null ? null : () => _showPhoto(person),
      child: Container(
        width: 58,
        height: 58,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: const Color(0xFF1E293B),
          border: Border.all(color: kAccent.withValues(alpha: 0.35)),
        ),
        clipBehavior: Clip.antiAlias,
        child: url == null
            ? Center(
                child: Text(
                  initials.isEmpty ? '?' : initials,
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontWeight: FontWeight.w900,
                    fontSize: 16,
                  ),
                ),
              )
            : Image.network(
                url,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => const Icon(Icons.person, color: kTextMuted),
              ),
      ),
    );
  }

  Widget _statusChip(Map<String, dynamic> person) {
    final status = person['noodgeval_status']?.toString() ?? 'WAG_OP_ONTVANG';
    String label;
    Color color;
    switch (status) {
      case 'GEEN_TOESTEL':
        label = 'Event-gas · geen app';
        color = Colors.purpleAccent;
        break;
      case 'KENNIS_GENEEM':
        label = 'Kennis geneem';
        color = Colors.green;
        break;
      case 'ONTVANG':
        label = 'Ontvang';
        color = Colors.blue;
        break;
      default:
        label = 'Wag op ontvang';
        color = Colors.orange;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.45)),
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(color: color, fontSize: 9, fontWeight: FontWeight.w800),
      ),
    );
  }

  Widget _personCard(Map<String, dynamic> person) {
    final busyKey = _personBusyKey(person);
    final busy = busyKey != null && _busyUsers.contains(busyKey);
    final name = person['volle_naam']?.toString() ?? 'Onbekende persoon';
    final type = person['tipe']?.toString() ?? 'Gebruiker';
    final number = person['nommer']?.toString().trim() ?? '';
    final eventName = person['event_name']?.toString().trim() ?? '';
    final isEventGuest = person['event_gas'] == true;

    return GlassCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _avatar(person),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                        color: kText1,
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      number.isEmpty ? type : '$type · $number',
                      style: GoogleFonts.inter(color: kTextMuted, fontSize: 11),
                    ),
                    if (isEventGuest && eventName.isNotEmpty) ...[
                      const SizedBox(height: 3),
                      Text(
                        'EVENT · $eventName',
                        style: GoogleFonts.inter(
                          color: Colors.purpleAccent,
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                    const SizedBox(height: 7),
                    _statusChip(person),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 46,
                  child: ElevatedButton.icon(
                    onPressed: busy || busyKey == null ? null : () => _markPerson(person, 'DAAR'),
                    icon: busy
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.check_circle_rounded, size: 19),
                    label: const Text('DAAR'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green.shade700,
                      foregroundColor: Colors.white,
                      disabledBackgroundColor: Colors.green.withValues(alpha: 0.25),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13)),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: SizedBox(
                  height: 46,
                  child: OutlinedButton.icon(
                    onPressed: busy || busyKey == null ? null : () => _markPerson(person, 'NIE_DAAR'),
                    icon: const Icon(Icons.close_rounded, size: 19),
                    label: const Text('NIE DAAR NIE'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.red.shade300,
                      side: BorderSide(color: Colors.red.withValues(alpha: 0.55)),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13)),
                      textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _notThereCard(Map<String, dynamic> person) {
    final busyKey = _personBusyKey(person);
    final busy = busyKey != null && _busyUsers.contains(busyKey);
    final name = person['volle_naam']?.toString() ?? 'Onbekende persoon';
    final type = person['tipe']?.toString() ?? 'Gebruiker';
    final number = person['nommer']?.toString().trim() ?? '';
    final eventName = person['event_name']?.toString().trim() ?? '';

    return Opacity(
      opacity: 0.78,
      child: GlassCard(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            _avatar(person),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(name, style: GoogleFonts.inter(color: kText1, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 3),
                  Text(
                    number.isEmpty ? type : '$type · $number',
                    style: GoogleFonts.inter(color: kTextMuted, fontSize: 11),
                  ),
                  if (eventName.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      'EVENT · $eventName',
                      style: GoogleFonts.inter(
                        color: Colors.purpleAccent,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                  const SizedBox(height: 6),
                  Text(
                    'NIE DAAR NIE',
                    style: GoogleFonts.inter(
                      color: Colors.red.shade300,
                      fontSize: 10,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            TextButton.icon(
              onPressed: busy || busyKey == null ? null : () => _restorePerson(person),
              icon: busy
                  ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.undo_rounded, size: 17),
              label: const Text('HERSTEL'),
              style: TextButton.styleFrom(
                foregroundColor: kAccent,
                textStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.w900),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _metricCard(String label, dynamic value, IconData icon, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 13),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(15),
          border: Border.all(color: color.withValues(alpha: 0.32)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(height: 5),
            Text(
              '${value ?? 0}',
              style: GoogleFonts.inter(color: kText1, fontSize: 24, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 2),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: GoogleFonts.inter(color: kTextMuted, fontSize: 9, fontWeight: FontWeight.w800),
            ),
          ],
        ),
      ),
    );
  }

  Widget _campusSelector() {
    if (_campuses.length <= 1) {
      return Row(
        children: [
          const Icon(Icons.location_on_rounded, size: 17, color: kAccent),
          const SizedBox(width: 7),
          Expanded(
            child: Text(
              _campus?.naam ?? 'Geen kampus',
              style: GoogleFonts.inter(color: kText2, fontSize: 12, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      );
    }

    return DropdownButtonHideUnderline(
      child: DropdownButton<KampusDto>(
        value: _campus,
        isExpanded: true,
        dropdownColor: const Color(0xFF111827),
        iconEnabledColor: kAccent,
        items: _campuses
            .map(
              (c) => DropdownMenuItem<KampusDto>(
                value: c,
                child: Text(c.naam, style: GoogleFonts.inter(color: kText1, fontSize: 12)),
              ),
            )
            .toList(),
        onChanged: _selectCampus,
      ),
    );
  }

  Widget _noEmergency() {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: [
        GlassCard(padding: const EdgeInsets.all(14), child: _campusSelector()),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 34),
          decoration: BoxDecoration(
            color: Colors.green.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: Colors.green.withValues(alpha: 0.35)),
          ),
          child: Column(
            children: [
              const Icon(Icons.shield_outlined, color: Colors.green, size: 48),
              const SizedBox(height: 12),
              Text(
                'Geen aktiewe noodgeval',
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(color: kText1, fontSize: 18, fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 6),
              Text(
                'Geen live WebSocket is nodig totdat ’n nood begin nie. MQTT bly die agtergrond-noodkanaal.',
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(color: kText2, fontSize: 11, height: 1.45),
              ),
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                height: 54,
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.red.shade700,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
                  ),
                  onPressed: _emergencyActionBusy || _campus?.kampusId == null
                      ? null
                      : _activateEmergency,
                  icon: _emergencyActionBusy
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.emergency_rounded),
                  label: const Text('AKTIVEER NOODGEVAL'),
                ),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: _checkingEmergency || _emergencyActionBusy
                    ? null
                    : () => _checkActiveEmergency(force: true),
                icon: _checkingEmergency
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.refresh_rounded),
                label: const Text('KONTROLEER NOU'),
              ),
            ],
          ),
        ),
        if (_error != null) ...[
          const SizedBox(height: 14),
          _errorCard(),
        ],
      ],
    );
  }

  Widget _errorCard() {
    return GlassCard(
      padding: const EdgeInsets.all(12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.warning_amber_rounded, color: Colors.orange, size: 20),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              _error ?? '',
              style: GoogleFonts.inter(color: kText2, fontSize: 11, height: 1.4),
            ),
          ),
        ],
      ),
    );
  }

  Widget _activeDashboard() {
    final activeRaw = _snapshot?['aktiewe_noodgeval'];
    final active = activeRaw is Map ? Map<String, dynamic>.from(activeRaw) : <String, dynamic>{};
    final waiting = _listFromSnapshot('wag_vir_kontrole').where(_matches).toList();
    final notThere = _listFromSnapshot('nie_daar_nie').where(_matches).toList();

    return RefreshIndicator(
      onRefresh: () => _checkActiveEmergency(force: true),
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 28),
        children: [
          GlassCard(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(child: _campusSelector()),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                      decoration: BoxDecoration(
                        color: (_socketConnected ? Colors.green : Colors.orange).withValues(alpha: 0.13),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.circle, size: 7, color: _socketConnected ? Colors.green : Colors.orange),
                          const SizedBox(width: 5),
                          Text(
                            _socketConnected ? 'LIVE' : 'HERKOPPEL',
                            style: GoogleFonts.inter(
                              color: _socketConnected ? Colors.green : Colors.orange,
                              fontSize: 9,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.emergency_rounded, color: Colors.red, size: 28),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            active['titel']?.toString() ?? 'NOODGEVAL AKTIEF',
                            style: GoogleFonts.inter(color: Colors.red.shade300, fontSize: 16, fontWeight: FontWeight.w900),
                          ),
                          if ((active['boodskap']?.toString() ?? '').isNotEmpty) ...[
                            const SizedBox(height: 4),
                            Text(
                              active['boodskap'].toString(),
                              style: GoogleFonts.inter(color: kText2, fontSize: 11, height: 1.35),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _emergencyActionBusy ? null : _resendEmergency,
                  icon: const Icon(Icons.campaign_rounded),
                  label: const Text('HERSTUUR'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.orange.shade300,
                    side: BorderSide(color: Colors.orange.withValues(alpha: 0.55)),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
              const SizedBox(width: 9),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _emergencyActionBusy ? null : _closeEmergency,
                  icon: _emergencyActionBusy
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                        )
                      : const Icon(Icons.stop_circle_outlined),
                  label: const Text('SLUIT NOOD'),
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.green.shade700,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              _metricCard('OP KAMPUS', _stats['op_kampus'], Icons.groups_rounded, kAccent),
              const SizedBox(width: 8),
              _metricCard('ONTVANG', _stats['ontvang'], Icons.mark_email_read_rounded, Colors.blue),
              const SizedBox(width: 8),
              _metricCard('KENNIS', _stats['kennis_geneem'], Icons.fact_check_rounded, Colors.green),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: Text(
                  'Wag vir kontrole: ${_stats['wag_vir_kontrole'] ?? 0}',
                  style: GoogleFonts.inter(color: kTextMuted, fontSize: 10, fontWeight: FontWeight.w700),
                ),
              ),
              Text(
                'Daar: ${_stats['daar'] ?? 0}  ·  Nie daar: ${_stats['nie_daar'] ?? 0}',
                style: GoogleFonts.inter(color: kTextMuted, fontSize: 10, fontWeight: FontWeight.w700),
              ),
            ],
          ),
          const SizedBox(height: 5),
          Text(
            'Event-gaste: ${_stats['event_gaste'] ?? 0}  ·  Intern: ${_stats['event_gaste_intern'] ?? 0}  ·  Ekstern: ${_stats['event_gaste_ekstern'] ?? 0}',
            style: GoogleFonts.inter(
              color: Colors.purpleAccent,
              fontSize: 10,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 15),
          TextField(
            controller: _searchController,
            style: GoogleFonts.inter(color: kText1, fontSize: 13),
            decoration: InputDecoration(
              hintText: 'Soek persoon op kampus...',
              hintStyle: GoogleFonts.inter(color: kTextMuted, fontSize: 12),
              prefixIcon: const Icon(Icons.search_rounded, color: kTextMuted),
              suffixIcon: _query.isEmpty
                  ? null
                  : IconButton(
                      onPressed: _searchController.clear,
                      icon: const Icon(Icons.close_rounded, color: kTextMuted),
                    ),
              filled: true,
              fillColor: const Color(0x12FFFFFF),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(15),
                borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(15),
                borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(15),
                borderSide: const BorderSide(color: kAccent),
              ),
            ),
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: Text(
                  'MENSE OP KAMPUS',
                  style: GoogleFonts.inter(color: kText1, fontSize: 12, fontWeight: FontWeight.w900, letterSpacing: 0.8),
                ),
              ),
              Text(
                '${waiting.length}',
                style: GoogleFonts.inter(color: kAccent, fontSize: 12, fontWeight: FontWeight.w900),
              ),
            ],
          ),
          const SizedBox(height: 5),
          Text(
            'Merk elke persoon as DAAR of NIE DAAR NIE.',
            style: GoogleFonts.inter(color: kTextMuted, fontSize: 10),
          ),
          const SizedBox(height: 10),
          if (waiting.isEmpty)
            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Text(
                _query.isEmpty ? 'Geen mense wag vir kontrole nie.' : 'Geen persoon pas by jou soektog nie.',
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(color: kText2, fontSize: 12),
              ),
            )
          else
            ...waiting.map(
              (person) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _personCard(person),
              ),
            ),
          const SizedBox(height: 18),
          Row(
            children: [
              const Icon(Icons.person_off_rounded, color: Colors.red, size: 19),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  'NIE DAAR NIE',
                  style: GoogleFonts.inter(color: kText1, fontSize: 12, fontWeight: FontWeight.w900, letterSpacing: 0.8),
                ),
              ),
              Text(
                '${notThere.length}',
                style: GoogleFonts.inter(color: Colors.red.shade300, fontSize: 12, fontWeight: FontWeight.w900),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (notThere.isEmpty)
            Text(
              _query.isEmpty ? 'Niemand is tans as “nie daar nie” gemerk nie.' : 'Geen persoon pas by jou soektog nie.',
              style: GoogleFonts.inter(color: kTextMuted, fontSize: 10),
            )
          else
            ...notThere.map(
              (person) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _notThereCard(person),
              ),
            ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            _errorCard(),
          ],
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
              title: 'Nood',
              subtitle: 'Live kampuskontrole',
              showBack: true,
            ),
            Expanded(
              child: _loadingCampuses
                  ? const Center(child: CircularProgressIndicator())
                  : _activeEmergencyId == null
                      ? RefreshIndicator(
                          onRefresh: () => _checkActiveEmergency(force: true),
                          child: _noEmergency(),
                        )
                      : _snapshot == null
                          ? Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const CircularProgressIndicator(),
                                const SizedBox(height: 12),
                                Text(
                                  'Koppel aan live nooddata...',
                                  style: GoogleFonts.inter(color: kText2, fontSize: 12),
                                ),
                                if (_error != null) ...[
                                  const SizedBox(height: 12),
                                  Padding(
                                    padding: const EdgeInsets.symmetric(horizontal: 18),
                                    child: _errorCard(),
                                  ),
                                ],
                              ],
                            )
                          : _activeDashboard(),
            ),
          ],
        ),
      ),
    );
  }
}
