import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';

import 'app_shared.dart';
import 'moon_api.dart';

class SaamryPinSelection {
  final double latitude;
  final double longitude;
  final String? beskrywing;
  final bool stoorAsVerstek;

  const SaamryPinSelection({
    required this.latitude,
    required this.longitude,
    this.beskrywing,
    this.stoorAsVerstek = false,
  });
}

class _SaamryAddressResult {
  final String displayName;
  final double latitude;
  final double longitude;

  const _SaamryAddressResult({
    required this.displayName,
    required this.latitude,
    required this.longitude,
  });

  factory _SaamryAddressResult.fromJson(Map<String, dynamic> json) {
    return _SaamryAddressResult(
      displayName: json['display_name']?.toString() ?? '',
      latitude: double.parse(json['lat'].toString()),
      longitude: double.parse(json['lon'].toString()),
    );
  }
}

LatLng _saamryDefaultMapCenter() => const LatLng(-30.5595, 22.9375);

Future<List<_SaamryAddressResult>> _searchSaamryAddresses(String rawQuery) async {
  final query = rawQuery.trim();
  if (query.length < 3) {
    throw Exception('Tik minstens 3 karakters van die adres');
  }

  final uri = Uri.https(
    'nominatim.openstreetmap.org',
    '/search',
    <String, String>{
      'format': 'jsonv2',
      'q': query,
      'limit': '6',
      'countrycodes': 'za',
      'addressdetails': '1',
    },
  );

  final response = await http.get(
    uri,
    headers: const <String, String>{
      'Accept': 'application/json',
      'User-Agent': 'MOON-Saamry/1.0',
    },
  );

  if (response.statusCode < 200 || response.statusCode >= 300) {
    throw Exception('Kon nie die adres soek nie (HTTP ${response.statusCode})');
  }

  final decoded = jsonDecode(response.body);
  if (decoded is! List) {
    throw Exception('Ongeldige antwoord op adressoektog');
  }

  return decoded
      .whereType<Map>()
      .map((item) => _SaamryAddressResult.fromJson(
            Map<String, dynamic>.from(item),
          ))
      .where((item) => item.displayName.trim().isNotEmpty)
      .toList();
}

class _AddressSearchPanel extends StatefulWidget {
  final TextEditingController controller;
  final bool enabled;
  final ValueChanged<_SaamryAddressResult> onSelected;

  const _AddressSearchPanel({
    required this.controller,
    required this.enabled,
    required this.onSelected,
  });

  @override
  State<_AddressSearchPanel> createState() => _AddressSearchPanelState();
}

class _AddressSearchPanelState extends State<_AddressSearchPanel> {
  bool _searching = false;
  String? _error;
  List<_SaamryAddressResult> _results = const [];

  Future<void> _search() async {
    if (!widget.enabled || _searching) return;

    setState(() {
      _searching = true;
      _error = null;
      _results = const [];
    });

    try {
      final results = await _searchSaamryAddresses(widget.controller.text);
      if (!mounted) return;
      setState(() {
        _results = results;
        _searching = false;
        if (results.isEmpty) {
          _error = 'Geen adres gevind nie. Probeer straat, voorstad en dorp/stad.';
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString().replaceFirst('Exception: ', '');
        _searching = false;
      });
    }
  }

  void _select(_SaamryAddressResult result) {
    widget.controller.text = result.displayName;
    widget.onSelected(result);
    setState(() {
      _results = const [];
      _error = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: widget.controller,
          enabled: widget.enabled && !_searching,
          textInputAction: TextInputAction.search,
          onSubmitted: (_) => _search(),
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: 'Adres',
            hintText: 'bv. 12 Kerkstraat, Springs, Gauteng',
            prefixIcon: const Icon(Icons.search_rounded, color: kTextMuted),
            labelStyle: const TextStyle(color: kTextMuted),
            hintStyle: const TextStyle(color: kTextMuted),
            filled: true,
            fillColor: Colors.white.withOpacity(0.05),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
        const SizedBox(height: 9),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: widget.enabled && !_searching ? _search : null,
            icon: _searching
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.location_searching_rounded),
            label: Text(_searching ? 'Soek adres...' : 'Soek Adres'),
          ),
        ),
        if (_error != null) ...[
          const SizedBox(height: 8),
          Text(
            _error!,
            style: GoogleFonts.inter(color: Colors.orangeAccent, fontSize: 11),
          ),
        ],
        if (_results.isNotEmpty) ...[
          const SizedBox(height: 10),
          Container(
            decoration: BoxDecoration(
              color: const Color(0xFF111827),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.white12),
            ),
            child: Column(
              children: [
                for (var i = 0; i < _results.length; i++) ...[
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.location_on_outlined, color: kAccent),
                    title: Text(
                      _results[i].displayName,
                      style: GoogleFonts.inter(color: kText1, fontSize: 11.5),
                    ),
                    onTap: () => _select(_results[i]),
                  ),
                  if (i != _results.length - 1)
                    const Divider(height: 1, color: Colors.white10),
                ],
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class SaamryPinPickerPage extends StatefulWidget {
  final String title;
  final String subtitle;
  final double? initialLatitude;
  final double? initialLongitude;
  final String? initialBeskrywing;
  final bool allowSaveAsDefault;

  const SaamryPinPickerPage({
    super.key,
    required this.title,
    required this.subtitle,
    this.initialLatitude,
    this.initialLongitude,
    this.initialBeskrywing,
    this.allowSaveAsDefault = false,
  });

  @override
  State<SaamryPinPickerPage> createState() => _SaamryPinPickerPageState();
}

class _SaamryPinPickerPageState extends State<SaamryPinPickerPage> {
  late final TextEditingController _addressController;
  LatLng? _selected;
  bool _saveAsDefault = false;

  @override
  void initState() {
    super.initState();
    _addressController = TextEditingController(text: widget.initialBeskrywing ?? '');
    if (widget.initialLatitude != null && widget.initialLongitude != null) {
      _selected = LatLng(widget.initialLatitude!, widget.initialLongitude!);
    }
  }

  @override
  void dispose() {
    _addressController.dispose();
    super.dispose();
  }

  void _useAddress(_SaamryAddressResult result) {
    setState(() {
      _selected = LatLng(result.latitude, result.longitude);
    });
  }

  @override
  Widget build(BuildContext context) {
    final center = _selected ?? _saamryDefaultMapCenter();

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: widget.title,
              subtitle: widget.subtitle,
              showBack: true,
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  GlassCard(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Tik die adres waar die bestuurder begin ry. Kies daarna die korrekte soekresultaat.',
                          style: GoogleFonts.inter(color: kText1, fontSize: 13),
                        ),
                        const SizedBox(height: 14),
                        _AddressSearchPanel(
                          controller: _addressController,
                          enabled: true,
                          onSelected: _useAddress,
                        ),
                        const SizedBox(height: 14),
                        Text(
                          _selected == null
                              ? 'Kies ’n adres om die ligging op die kaart te bevestig.'
                              : 'Adres gekies — bevestig die ligging hieronder.',
                          style: GoogleFonts.inter(color: kText2, fontSize: 11.5),
                        ),
                        const SizedBox(height: 10),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(16),
                          child: SizedBox(
                            height: 330,
                            child: FlutterMap(
                              key: ValueKey('${_selected?.latitude}-${_selected?.longitude}'),
                              options: MapOptions(
                                initialCenter: center,
                                initialZoom: _selected == null ? 5.5 : 16,
                              ),
                              children: [
                                TileLayer(
                                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                                  userAgentPackageName: 'studente_mobile_flutter_app',
                                ),
                                if (_selected != null)
                                  MarkerLayer(
                                    markers: [
                                      Marker(
                                        point: _selected!,
                                        width: 64,
                                        height: 64,
                                        child: const Icon(
                                          Icons.location_pin,
                                          color: kAccent,
                                          size: 48,
                                        ),
                                      ),
                                    ],
                                  ),
                                RichAttributionWidget(
                                  attributions: [
                                    TextSourceAttribution('OpenStreetMap contributors'),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                        if (widget.allowSaveAsDefault) ...[
                          const SizedBox(height: 10),
                          CheckboxListTile(
                            contentPadding: EdgeInsets.zero,
                            value: _saveAsDefault,
                            activeColor: kAccent,
                            checkColor: Colors.black,
                            title: Text(
                              'Stoor ook as my gewone opteladres',
                              style: GoogleFonts.inter(color: kText1, fontSize: 11.5),
                            ),
                            onChanged: (value) =>
                                setState(() => _saveAsDefault = value == true),
                          ),
                        ],
                        const SizedBox(height: 14),
                        GradientActionButton(
                          label: _selected == null
                              ? 'Kies eers ’n adres'
                              : 'Gebruik Hierdie Adres',
                          onTap: _selected == null
                              ? () {}
                              : () {
                                  Navigator.pop(
                                    context,
                                    SaamryPinSelection(
                                      latitude: _selected!.latitude,
                                      longitude: _selected!.longitude,
                                      beskrywing: _addressController.text.trim().isEmpty
                                          ? null
                                          : _addressController.text.trim(),
                                      stoorAsVerstek: _saveAsDefault,
                                    ),
                                  );
                                },
                          height: 50,
                        ),
                      ],
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

class SaamryDefaultPickupPage extends StatefulWidget {
  const SaamryDefaultPickupPage({super.key});

  @override
  State<SaamryDefaultPickupPage> createState() => _SaamryDefaultPickupPageState();
}

class _SaamryDefaultPickupPageState extends State<SaamryDefaultPickupPage> {
  bool _loading = true;
  bool _saving = false;
  SaamryPickupProfileDto? _profile;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final profile = await MoonApi.fetchSaamryPickupProfile();
      if (!mounted) return;
      setState(() {
        _profile = profile;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _changeAddress() async {
    final selected = await Navigator.push<SaamryPinSelection>(
      context,
      MaterialPageRoute(
        builder: (_) => SaamryPinPickerPage(
          title: 'My gewone opteladres',
          subtitle: 'Word as verstek vir nuwe Saamry-ritte gebruik',
          initialLatitude: _profile?.latitude,
          initialLongitude: _profile?.longitude,
          initialBeskrywing: _profile?.beskrywing,
        ),
      ),
    );
    if (selected == null || !mounted) return;
    final address = selected.beskrywing?.trim() ?? '';
    if (address.isEmpty) return;

    setState(() => _saving = true);
    try {
      final profile = await MoonApi.saveSaamryPickupProfile(
        latitude: selected.latitude,
        longitude: selected.longitude,
        beskrywing: address,
      );
      if (!mounted) return;
      setState(() {
        _profile = profile;
        _saving = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Gewone opteladres is gestoor')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
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
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'My opteladres',
              subtitle: 'Jou gewone Saamry-optelpunt',
              showBack: true,
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  GlassCard(
                    padding: const EdgeInsets.all(16),
                    child: _loading
                        ? Center(child: CircularProgressIndicator())
                        : Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(
                                Icons.location_on_rounded,
                                color: kAccent,
                                size: 40,
                              ),
                              const SizedBox(height: 12),
                              Text(
                                _profile == null
                                    ? 'Geen gewone opteladres gestel nie'
                                    : 'Jou gewone opteladres',
                                style: GoogleFonts.inter(
                                  color: kText1,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              const SizedBox(height: 7),
                              Text(
                                _profile?.beskrywing ??
                                    'Stel dit een keer. Wanneer jy later deel van ’n nuwe Saamry-rit is, word hierdie adres vooraf ingevul maar jy moet dit steeds vir daardie rit bevestig.',
                                style: GoogleFonts.inter(
                                  color: kText2,
                                  fontSize: 12,
                                  height: 1.4,
                                ),
                              ),
                              if (_error != null) ...[
                                const SizedBox(height: 10),
                                Text(
                                  _error!,
                                  style: GoogleFonts.inter(
                                    color: Colors.redAccent,
                                    fontSize: 11.5,
                                  ),
                                ),
                              ],
                              const SizedBox(height: 16),
                              GradientActionButton(
                                label: _saving
                                    ? 'Stoor...'
                                    : (_profile == null
                                        ? 'Stel opteladres'
                                        : 'Verander opteladres'),
                                onTap: _saving ? () {} : _changeAddress,
                                height: 50,
                              ),
                            ],
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

class SaamryPickupMapPage extends StatefulWidget {
  final SaamryGroupDto group;
  final SaamryEventDto event;

  const SaamryPickupMapPage({
    super.key,
    required this.group,
    required this.event,
  });

  @override
  State<SaamryPickupMapPage> createState() => _SaamryPickupMapPageState();
}

class _SaamryPickupMapPageState extends State<SaamryPickupMapPage> {
  late SaamryEventDto _event;
  late final TextEditingController _addressController;
  LatLng? _draft;
  bool _saving = false;
  bool _saveAsDefault = false;

  SaamryEventMemberDto? get _me {
    for (final member in _event.lede) {
      if (member.isMyne) return member;
    }
    return null;
  }

  @override
  void initState() {
    super.initState();
    _event = widget.event;
    final me = _me;
    _addressController = TextEditingController(text: me?.pickupBeskrywing ?? '');
    if (me?.pickupLatitude != null && me?.pickupLongitude != null) {
      _draft = LatLng(me!.pickupLatitude!, me.pickupLongitude!);
    }
  }

  @override
  void dispose() {
    _addressController.dispose();
    super.dispose();
  }

  List<SaamryEventMemberDto> get _visiblePins => _event.lede
      .where((m) => m.pickupLatitude != null && m.pickupLongitude != null)
      .toList();

  LatLng _center() {
    final points = _visiblePins
        .map((m) => LatLng(m.pickupLatitude!, m.pickupLongitude!))
        .toList();
    if (_draft != null) points.add(_draft!);
    if (points.isEmpty) return _saamryDefaultMapCenter();
    final lat = points.map((p) => p.latitude).reduce((a, b) => a + b) / points.length;
    final lon = points.map((p) => p.longitude).reduce((a, b) => a + b) / points.length;
    return LatLng(lat, lon);
  }

  void _selectAddress(_SaamryAddressResult result) {
    setState(() {
      _draft = LatLng(result.latitude, result.longitude);
    });
  }

  Future<void> _save() async {
    final point = _draft;
    final address = _addressController.text.trim();
    if (point == null || address.isEmpty || _saving) return;

    setState(() => _saving = true);
    try {
      final updated = await MoonApi.updateSaamryPickup(
        eventId: _event.eventId,
        latitude: point.latitude,
        longitude: point.longitude,
        beskrywing: address,
        stoorAsVerstek: _saveAsDefault,
      );
      if (!mounted) return;
      setState(() {
        _event = updated;
        _saving = false;
        _saveAsDefault = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Opteladres is gestoor')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
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
    final canEdit = _event.status == 'AKTIEF' && _event.isDeelnemer;
    final visible = _visiblePins;
    final initialZoom = visible.isEmpty ? 5.5 : 12.5;

    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            AppScreenHeader(
              title: 'Opteladresse',
              subtitle: widget.group.naam,
              showBack: true,
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  GlassCard(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.location_on_rounded, color: kAccent),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _event.isBestuurder
                                    ? '${_event.pickupGereed}/${_event.pickupTotaal} adresse gereed'
                                    : 'Jou opteladres + bestuurder se beginadres',
                                style: GoogleFonts.inter(
                                  color: kText1,
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          _event.isBestuurder
                              ? 'As bestuurder/admin kan jy al die deelnemers se opteladresse sien. Tik jou eie beginadres hieronder om dit te verander.'
                              : _me?.pickupLatitude != null && _me?.pickupGestel != true
                                  ? 'Jou gewone opteladres is vooraf ingevul. Bevestig dit vir hierdie rit of kies ’n ander adres.'
                                  : 'Tik jou opteladres hieronder. Ander passasiers se presiese adresse bly privaat.',
                          style: GoogleFonts.inter(color: kText2, fontSize: 11.5),
                        ),
                        if (canEdit) ...[
                          const SizedBox(height: 14),
                          _AddressSearchPanel(
                            controller: _addressController,
                            enabled: !_saving,
                            onSelected: _selectAddress,
                          ),
                        ],
                        const SizedBox(height: 14),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(16),
                          child: SizedBox(
                            height: 390,
                            child: FlutterMap(
                              key: ValueKey(
                                '${_event.eventId}-${visible.length}-${_draft?.latitude}-${_draft?.longitude}',
                              ),
                              options: MapOptions(
                                initialCenter: _center(),
                                initialZoom: initialZoom,
                              ),
                              children: [
                                TileLayer(
                                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                                  userAgentPackageName: 'studente_mobile_flutter_app',
                                ),
                                MarkerLayer(
                                  markers: [
                                    ...visible.map(
                                      (member) => Marker(
                                        point: LatLng(
                                          member.pickupLatitude!,
                                          member.pickupLongitude!,
                                        ),
                                        width: 110,
                                        height: 72,
                                        child: Column(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            Icon(
                                              member.isBestuurder
                                                  ? Icons.directions_car_filled_rounded
                                                  : Icons.location_pin,
                                              color: member.isBestuurder
                                                  ? Colors.orangeAccent
                                                  : kAccent,
                                              size: 38,
                                            ),
                                            Container(
                                              padding: const EdgeInsets.symmetric(
                                                horizontal: 6,
                                                vertical: 2,
                                              ),
                                              decoration: BoxDecoration(
                                                color: const Color(0xDD111827),
                                                borderRadius: BorderRadius.circular(8),
                                              ),
                                              child: Text(
                                                member.gebruiker.naam,
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis,
                                                style: const TextStyle(
                                                  color: Colors.white,
                                                  fontSize: 9,
                                                  fontWeight: FontWeight.w700,
                                                ),
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                    if (_draft != null)
                                      Marker(
                                        point: _draft!,
                                        width: 56,
                                        height: 56,
                                        child: const Icon(
                                          Icons.my_location_rounded,
                                          color: Colors.greenAccent,
                                          size: 40,
                                        ),
                                      ),
                                  ],
                                ),
                                RichAttributionWidget(
                                  attributions: [
                                    TextSourceAttribution('OpenStreetMap contributors'),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                        if (canEdit) ...[
                          const SizedBox(height: 8),
                          CheckboxListTile(
                            contentPadding: EdgeInsets.zero,
                            value: _saveAsDefault,
                            activeColor: kAccent,
                            checkColor: Colors.black,
                            title: Text(
                              'Stoor hierdie ook as my gewone opteladres',
                              style: GoogleFonts.inter(color: kText1, fontSize: 11.5),
                            ),
                            onChanged: _saving
                                ? null
                                : (value) => setState(
                                      () => _saveAsDefault = value == true,
                                    ),
                          ),
                          const SizedBox(height: 8),
                          GradientActionButton(
                            label: _saving
                                ? 'Stoor...'
                                : (_me?.pickupGestel == true
                                    ? 'Verander My Adres'
                                    : (_draft != null ? 'Bevestig Hierdie Adres' : 'Stoor My Adres')),
                            onTap: _saving ||
                                    _draft == null ||
                                    _addressController.text.trim().isEmpty
                                ? () {}
                                : _save,
                            height: 50,
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  GlassCard(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'RITLEDE',
                          style: GoogleFonts.inter(
                            color: kTextMuted,
                            fontSize: 9,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1,
                          ),
                        ),
                        const SizedBox(height: 10),
                        ..._event.lede.map(
                          (member) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(
                                  member.pickupGestel
                                      ? Icons.check_circle_rounded
                                      : Icons.location_off_rounded,
                                  color: member.pickupGestel
                                      ? Colors.greenAccent
                                      : Colors.orangeAccent,
                                  size: 20,
                                ),
                                const SizedBox(width: 9),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '${member.gebruiker.volleNaam}${member.isMyne ? ' · Jy' : ''}',
                                        style: GoogleFonts.inter(
                                          color: kText1,
                                          fontSize: 12.5,
                                          fontWeight: FontWeight.w700,
                                        ),
                                      ),
                                      if (member.pickupBeskrywing?.trim().isNotEmpty == true)
                                        Text(
                                          member.pickupBeskrywing!,
                                          style: GoogleFonts.inter(
                                            color: kTextMuted,
                                            fontSize: 10.5,
                                          ),
                                        ),
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Text(
                                  member.isBestuurder
                                      ? 'BESTUURDER'
                                      : (member.pickupGestel ? 'ADRES GEREED' : 'WAG VIR ADRES'),
                                  style: TextStyle(
                                    color: member.pickupGestel
                                        ? kAccent
                                        : Colors.orangeAccent,
                                    fontSize: 8.5,
                                    fontWeight: FontWeight.w900,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
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
