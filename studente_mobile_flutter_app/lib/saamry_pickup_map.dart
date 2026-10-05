import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:latlong2/latlong.dart';

import 'app_shared.dart';
import 'moon_api.dart';

class SaamryPinSelection {
  final double latitude;
  final double longitude;
  final String? beskrywing;

  const SaamryPinSelection({
    required this.latitude,
    required this.longitude,
    this.beskrywing,
  });
}

LatLng _saamryDefaultMapCenter() => const LatLng(-30.5595, 22.9375);

class SaamryPinPickerPage extends StatefulWidget {
  final String title;
  final String subtitle;
  final double? initialLatitude;
  final double? initialLongitude;
  final String? initialBeskrywing;

  const SaamryPinPickerPage({
    super.key,
    required this.title,
    required this.subtitle,
    this.initialLatitude,
    this.initialLongitude,
    this.initialBeskrywing,
  });

  @override
  State<SaamryPinPickerPage> createState() => _SaamryPinPickerPageState();
}

class _SaamryPinPickerPageState extends State<SaamryPinPickerPage> {
  late final TextEditingController _noteController;
  LatLng? _selected;

  @override
  void initState() {
    super.initState();
    _noteController = TextEditingController(text: widget.initialBeskrywing ?? '');
    if (widget.initialLatitude != null && widget.initialLongitude != null) {
      _selected = LatLng(widget.initialLatitude!, widget.initialLongitude!);
    }
  }

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
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
                          'Tik op die kaart waar die Driver begin ry.',
                          style: GoogleFonts.inter(color: kText1, fontSize: 13),
                        ),
                        const SizedBox(height: 12),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(16),
                          child: SizedBox(
                            height: 390,
                            child: FlutterMap(
                              options: MapOptions(
                                initialCenter: center,
                                initialZoom: _selected == null ? 5.5 : 15,
                                onTap: (_, point) => setState(() => _selected = point),
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
                        const SizedBox(height: 14),
                        TextField(
                          controller: _noteController,
                          maxLength: 200,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            labelText: 'Beskrywing (opsioneel)',
                            hintText: 'bv. Hoofhek, Engen, voor woonstel',
                            labelStyle: const TextStyle(color: kTextMuted),
                            hintStyle: const TextStyle(color: kTextMuted),
                            filled: true,
                            fillColor: Colors.white.withOpacity(0.05),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(14),
                            ),
                          ),
                        ),
                        const SizedBox(height: 6),
                        GradientActionButton(
                          label: _selected == null ? 'Kies eers ’n pin' : 'Gebruik Hierdie Pin',
                          onTap: _selected == null
                              ? () {}
                              : () {
                                  Navigator.pop(
                                    context,
                                    SaamryPinSelection(
                                      latitude: _selected!.latitude,
                                      longitude: _selected!.longitude,
                                      beskrywing: _noteController.text.trim().isEmpty
                                          ? null
                                          : _noteController.text.trim(),
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
  late final TextEditingController _noteController;
  LatLng? _draft;
  bool _saving = false;

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
    _noteController = TextEditingController(text: me?.pickupBeskrywing ?? '');
    if (me?.pickupLatitude != null && me?.pickupLongitude != null) {
      _draft = LatLng(me!.pickupLatitude!, me.pickupLongitude!);
    }
  }

  @override
  void dispose() {
    _noteController.dispose();
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

  Future<void> _save() async {
    final point = _draft;
    if (point == null || _saving) return;
    setState(() => _saving = true);
    try {
      final updated = await MoonApi.updateSaamryPickup(
        eventId: _event.eventId,
        latitude: point.latitude,
        longitude: point.longitude,
        beskrywing: _noteController.text,
      );
      if (!mounted) return;
      setState(() {
        _event = updated;
        _saving = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Optel-pin is gestoor')),
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
              title: 'Pickup-kaart',
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
                                    ? '${_event.pickupGereed}/${_event.pickupTotaal} optelpunte gereed'
                                    : 'Jou optelpunt + Driver se beginpunt',
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
                              ? 'As Driver/Admin kan jy al die deelnemers se pins sien. Tik op die kaart om jou eie begin-pin te verander.'
                              : 'Tik op die kaart om jou eie optelpunt te stel of te verander. Ander passasiers se presiese pins bly privaat.',
                          style: GoogleFonts.inter(color: kText2, fontSize: 11.5),
                        ),
                        const SizedBox(height: 12),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(16),
                          child: SizedBox(
                            height: 420,
                            child: FlutterMap(
                              key: ValueKey('${_event.eventId}-${visible.length}-${_draft?.latitude}-${_draft?.longitude}'),
                              options: MapOptions(
                                initialCenter: _center(),
                                initialZoom: initialZoom,
                                onTap: canEdit
                                    ? (_, point) => setState(() => _draft = point)
                                    : null,
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
                          const SizedBox(height: 14),
                          TextField(
                            controller: _noteController,
                            maxLength: 200,
                            style: const TextStyle(color: Colors.white),
                            decoration: InputDecoration(
                              labelText: _event.isBestuurder
                                  ? 'Beginpunt beskrywing'
                                  : 'Optelpunt beskrywing',
                              hintText: 'bv. Hoofhek, Engen, voor woonstel',
                              labelStyle: const TextStyle(color: kTextMuted),
                              hintStyle: const TextStyle(color: kTextMuted),
                              filled: true,
                              fillColor: Colors.white.withOpacity(0.05),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                            ),
                          ),
                          const SizedBox(height: 6),
                          GradientActionButton(
                            label: _saving
                                ? 'Stoor...'
                                : (_me?.pickupGestel == true
                                    ? 'Verander My Pin'
                                    : 'Stoor My Pin'),
                            onTap: _saving || _draft == null ? () {} : _save,
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
                          'EVENT-LEDE',
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
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Row(
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
                                Text(
                                  member.isBestuurder
                                      ? 'DRIVER'
                                      : (member.pickupGestel ? 'PIN GEREED' : 'WAG VIR PIN'),
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
