import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_shared.dart';
import 'moon_api.dart';

class SaamryRecommendationPreview extends StatefulWidget {
  final Set<int> pendingFriendIds;
  final VoidCallback? onFriendChanged;

  const SaamryRecommendationPreview({
    super.key,
    this.pendingFriendIds = const <int>{},
    this.onFriendChanged,
  });

  @override
  State<SaamryRecommendationPreview> createState() =>
      _SaamryRecommendationPreviewState();
}

class _SaamryRecommendationPreviewState
    extends State<SaamryRecommendationPreview> {
  bool _loading = true;
  String? _error;
  SaamryProfileDto? _profile;
  List<SaamryRecommendationDto> _items = const [];
  final Set<int> _sentIds = <int>{};

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _cleanError(Object error) =>
      error.toString().replaceFirst('Exception: ', '');

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }

    SaamryProfileDto? profile;
    List<SaamryRecommendationDto> items = const [];
    Object? firstError;

    try {
      profile = await MoonApi.fetchSaamryProfile();
    } catch (e) {
      firstError = e;
    }

    try {
      items = await MoonApi.fetchSaamryRecommendations(limiet: 3);
    } catch (e) {
      firstError ??= e;
    }

    if (!mounted) return;
    setState(() {
      _profile = profile;
      _items = items;
      _error = firstError == null ? null : _cleanError(firstError);
      _loading = false;
    });
  }

  Future<void> _openSettings() async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(builder: (_) => const SaamryProfileSettingsPage()),
    );
    if (changed == true) await _load();
  }

  Future<void> _openAll() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (_) => SaamryRecommendationsPage(
          pendingFriendIds: <int>{
            ...widget.pendingFriendIds,
            ..._sentIds,
          },
          onFriendChanged: widget.onFriendChanged,
        ),
      ),
    );
    if (mounted) await _load();
  }

  Future<void> _sendFriendRequest(SaamryRecommendationDto item) async {
    if (_sentIds.contains(item.gebruikerId) ||
        widget.pendingFriendIds.contains(item.gebruikerId) ||
        item.isReedsVriend) {
      return;
    }
    try {
      await MoonApi.sendSaamryFriendRequest(item.gebruikerId);
      if (!mounted) return;
      setState(() => _sentIds.add(item.gebruikerId));
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Vriendskapversoek aan ${item.volleNaam} gestuur')),
      );
      widget.onFriendChanged?.call();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(_cleanError(e)),
        ),
      );
    }
  }

  bool get _profileIncomplete {
    final p = _profile;
    if (p == null) return true;
    return p.voorstad.trim().isEmpty || p.kampusId == null;
  }

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.star, color: kAccent, size: 22),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Aanbeveel vir jou',
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 15,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              IconButton(
                tooltip: 'Saamry-voorkeure',
                onPressed: _openSettings,
                icon: const Icon(Icons.tune, color: kAccent, size: 20),
              ),
              IconButton(
                tooltip: 'Herlaai aanbevelings',
                onPressed: _loading ? null : _load,
                icon: const Icon(Icons.refresh, color: kAccent, size: 20),
              ),
            ],
          ),
          Text(
            'Pasmaats wat volgens jou Saamry-profiel aanbeveel word.',
            style: GoogleFonts.inter(color: kTextMuted, fontSize: 11),
          ),
          if (_profileIncomplete) ...[
            const SizedBox(height: 12),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.orange.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Colors.orange.withValues(alpha: 0.30),
                ),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, color: Colors.orangeAccent),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Voltooi jou voorstad en kampus vir meer akkurate aanbevelings.',
                      style: GoogleFonts.inter(color: kText2, fontSize: 11.5),
                    ),
                  ),
                  TextButton(
                    onPressed: _openSettings,
                    child: const Text('Stel op'),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 12),
          if (_loading)
            const Center(
              child: Padding(
                padding: EdgeInsets.symmetric(vertical: 18),
                child: CircularProgressIndicator(),
              ),
            )
          else if (_error != null && _items.isEmpty)
            _RecommendationEmptyState(
              icon: Icons.error_outline,
              message: _error!,
              actionLabel: 'Probeer weer',
              onAction: _load,
            )
          else if (_items.isEmpty)
            _RecommendationEmptyState(
              icon: Icons.people_outline,
              message:
                  'Geen geskikte aanbevelings is tans bo die minimum telling nie.',
              actionLabel: 'Wysig voorkeure',
              onAction: _openSettings,
            )
          else ...[
            ..._items.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: SaamryRecommendationCard(
                  item: item,
                  pending: widget.pendingFriendIds.contains(item.gebruikerId) ||
                      _sentIds.contains(item.gebruikerId),
                  onFriendRequest: () => _sendFriendRequest(item),
                ),
              ),
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: _openAll,
                icon: const Icon(Icons.arrow_forward, size: 18),
                label: const Text('Sien alle aanbevelings'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class SaamryRecommendationsPage extends StatefulWidget {
  final Set<int> pendingFriendIds;
  final VoidCallback? onFriendChanged;

  const SaamryRecommendationsPage({
    super.key,
    this.pendingFriendIds = const <int>{},
    this.onFriendChanged,
  });

  @override
  State<SaamryRecommendationsPage> createState() =>
      _SaamryRecommendationsPageState();
}

class _SaamryRecommendationsPageState extends State<SaamryRecommendationsPage> {
  bool _loading = true;
  String? _error;
  List<SaamryRecommendationDto> _items = const [];
  final Set<int> _sentIds = <int>{};

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _cleanError(Object error) =>
      error.toString().replaceFirst('Exception: ', '');

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await MoonApi.fetchSaamryRecommendations(limiet: 20);
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _cleanError(e);
        _loading = false;
      });
    }
  }

  Future<void> _sendFriendRequest(SaamryRecommendationDto item) async {
    if (_sentIds.contains(item.gebruikerId) ||
        widget.pendingFriendIds.contains(item.gebruikerId) ||
        item.isReedsVriend) {
      return;
    }
    try {
      await MoonApi.sendSaamryFriendRequest(item.gebruikerId);
      if (!mounted) return;
      setState(() => _sentIds.add(item.gebruikerId));
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Vriendskapversoek aan ${item.volleNaam} gestuur')),
      );
      widget.onFriendChanged?.call();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(_cleanError(e)),
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
            const AppScreenHeader(
              title: 'Aanbeveel vir jou',
              subtitle: 'Saamry-versoenbaarheid',
              showBack: true,
            ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: _load,
                child: _loading && _items.isEmpty
                    ? ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        children: const [
                          SizedBox(height: 160),
                          Center(child: CircularProgressIndicator()),
                        ],
                      )
                    : ListView(
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.all(16),
                        children: [
                          if (_error != null)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: Text(
                                _error!,
                                style: const TextStyle(color: Colors.red),
                              ),
                            ),
                          if (_items.isEmpty)
                            _RecommendationEmptyState(
                              icon: Icons.people_outline,
                              message: 'Geen geskikte aanbevelings gevind nie.',
                              actionLabel: 'Herlaai',
                              onAction: _load,
                            )
                          else
                            ..._items.map(
                              (item) => Padding(
                                padding: const EdgeInsets.only(bottom: 12),
                                child: SaamryRecommendationCard(
                                  item: item,
                                  pending: widget.pendingFriendIds
                                          .contains(item.gebruikerId) ||
                                      _sentIds.contains(item.gebruikerId),
                                  onFriendRequest: () =>
                                      _sendFriendRequest(item),
                                ),
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

class SaamryRecommendationCard extends StatelessWidget {
  final SaamryRecommendationDto item;
  final bool pending;
  final VoidCallback? onFriendRequest;

  const SaamryRecommendationCard({
    super.key,
    required this.item,
    required this.pending,
    this.onFriendRequest,
  });

  Color get _qualityColor {
    switch (item.gehalte.toUpperCase()) {
      case 'UITSTEKEND':
        return Colors.greenAccent;
      case 'GOED':
        return Colors.lightBlueAccent;
      case 'MATIG':
        return Colors.orangeAccent;
      default:
        return kText2;
    }
  }

  Widget _avatar() {
    final raw = item.fotoUrl?.trim() ?? '';
    final imageUrl = raw.isEmpty
        ? null
        : (raw.startsWith('http') ? raw : '${MoonApi.baseUrl}$raw');
    return CircleAvatar(
      radius: 23,
      backgroundColor: Colors.white10,
      backgroundImage: imageUrl == null ? null : NetworkImage(imageUrl),
      child: imageUrl == null
          ? Text(
              item.naam.isEmpty ? '?' : item.naam[0].toUpperCase(),
              style: GoogleFonts.inter(
                color: kAccent,
                fontWeight: FontWeight.w800,
              ),
            )
          : null,
    );
  }

  @override
  Widget build(BuildContext context) {
    final commonDays = item.gemeenskaplikeDae.isEmpty
        ? 'Geen gemeenskaplike dae'
        : item.gemeenskaplikeDae.join(', ');

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.035),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: kBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _avatar(),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.volleNaam,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                        color: kText1,
                        fontSize: 13.5,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '${item.saamryRol} · ${item.voorstad}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: GoogleFonts.inter(
                        color: kTextMuted,
                        fontSize: 10.5,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 7,
                ),
                decoration: BoxDecoration(
                  color: _qualityColor.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _qualityColor.withValues(alpha: 0.40),
                  ),
                ),
                child: Column(
                  children: [
                    Text(
                      '${item.totaleTelling.toStringAsFixed(0)}%',
                      style: GoogleFonts.inter(
                        color: _qualityColor,
                        fontSize: 15,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      item.gehalte,
                      style: GoogleFonts.inter(
                        color: _qualityColor,
                        fontSize: 7.5,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.event_available_rounded,
                color: kAccent,
                size: 17,
              ),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  'Gemeenskaplike kampusdae: $commonDays',
                  style: GoogleFonts.inter(
                    color: kText2,
                    fontSize: 10.5,
                    height: 1.35,
                  ),
                ),
              ),
            ],
          ),
          if (item.besteDag != null && item.besteDag!.trim().isNotEmpty) ...[
            const SizedBox(height: 5),
            Row(
              children: [
                const Icon(
                  Icons.star_outline_rounded,
                  color: kTextMuted,
                  size: 16,
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: Text(
                    'Beste gemeenskaplike dag: ${item.besteDag}',
                    style: GoogleFonts.inter(
                      color: kTextMuted,
                      fontSize: 10.5,
                    ),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 11),
          SizedBox(
            width: double.infinity,
            child: item.isReedsVriend
                ? const _FriendStateButton(label: 'Reeds vriende')
                : pending
                    ? const _FriendStateButton(label: 'Versoek gestuur')
                    : ElevatedButton.icon(
                        onPressed: onFriendRequest,
                        icon: const Icon(Icons.person_add, size: 17),
                        label: const Text('Voeg as vriend'),
                      ),
          ),
        ],
      ),
    );
  }
}

class SaamryProfileSettingsPage extends StatefulWidget {
  const SaamryProfileSettingsPage({super.key});

  @override
  State<SaamryProfileSettingsPage> createState() =>
      _SaamryProfileSettingsPageState();
}

class _SaamryProfileSettingsPageState
    extends State<SaamryProfileSettingsPage> {
  final TextEditingController _suburbController = TextEditingController();
  bool _loading = true;
  bool _saving = false;
  String? _error;
  String _role = 'BEIDE';
  int? _campusId;
  int _maxDetour = 15;
  bool _active = true;
  List<KampusDto> _campuses = const [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _suburbController.dispose();
    super.dispose();
  }

  String _cleanError(Object error) =>
      error.toString().replaceFirst('Exception: ', '');

  Future<void> _load() async {
    try {
      final profile = await MoonApi.fetchSaamryProfile();
      final campuses = await MoonApi.fetchKampusse();
      if (!mounted) return;
      setState(() {
        _suburbController.text = profile.voorstad;
        _role = profile.rolTipe;
        _campusId = profile.kampusId;
        _maxDetour = profile.maksOmpadMinute;
        _active = profile.isAktiefSaamryer;
        _campuses = campuses.where((k) => k.kampusId != null).toList();
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _cleanError(e);
        _loading = false;
      });
    }
  }

  Future<void> _save() async {
    final suburb = _suburbController.text.trim();
    if (suburb.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Vul asseblief jou voorstad in')),
      );
      return;
    }
    if (_campusId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Kies asseblief jou gewone kampus')),
      );
      return;
    }
    if (_saving) return;
    setState(() => _saving = true);
    try {
      await MoonApi.updateSaamryProfile(
        rolTipe: _role,
        voorstad: suburb,
        kampusId: _campusId,
        maksOmpadMinute: _maxDetour,
        isAktiefSaamryer: _active,
      );
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          backgroundColor: Colors.red,
          content: Text(_cleanError(e)),
        ),
      );
    }
  }

  InputDecoration _decoration(String label) => InputDecoration(
        labelText: label,
        labelStyle: const TextStyle(color: kTextMuted),
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.04),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: kBorder),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kBg,
      body: SafeArea(
        child: Column(
          children: [
            const AppScreenHeader(
              title: 'Saamry-voorkeure',
              subtitle: 'Vir aanbevelings',
              showBack: true,
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : ListView(
                      padding: const EdgeInsets.all(16),
                      children: [
                        if (_error != null) ...[
                          Text(_error!, style: const TextStyle(color: Colors.red)),
                          const SizedBox(height: 12),
                        ],
                        GlassCard(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Jou rol, voorstad en kampus word vir aanbevelings gebruik. Die maksimum ompad word reeds gestoor vir latere roetebeplanning. Jou rit se opteladres bly apart.',
                                style: GoogleFonts.inter(
                                  color: kText2,
                                  fontSize: 11.5,
                                  height: 1.4,
                                ),
                              ),
                              const SizedBox(height: 16),
                              DropdownButtonFormField<String>(
                                value: _role,
                                dropdownColor: const Color(0xFF111827),
                                decoration: _decoration('Saamry-rol'),
                                items: const [
                                  DropdownMenuItem(
                                    value: 'BESTUURDER',
                                    child: Text('Slegs Bestuurder'),
                                  ),
                                  DropdownMenuItem(
                                    value: 'PASSASIER',
                                    child: Text('Slegs Passasier'),
                                  ),
                                  DropdownMenuItem(
                                    value: 'BEIDE',
                                    child: Text('Bestuurder of Passasier'),
                                  ),
                                ],
                                onChanged: (value) {
                                  if (value != null) setState(() => _role = value);
                                },
                              ),
                              const SizedBox(height: 12),
                              TextField(
                                controller: _suburbController,
                                style: const TextStyle(color: kText1),
                                textCapitalization: TextCapitalization.words,
                                decoration: _decoration('Voorstad'),
                              ),
                              const SizedBox(height: 12),
                              DropdownButtonFormField<int>(
                                value: _campusId,
                                dropdownColor: const Color(0xFF111827),
                                decoration: _decoration('Gewone kampus'),
                                items: _campuses
                                    .map(
                                      (campus) => DropdownMenuItem<int>(
                                        value: campus.kampusId!,
                                        child: Text(campus.naam),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (value) =>
                                    setState(() => _campusId = value),
                              ),
                              const SizedBox(height: 12),
                              const SizedBox(height: 16),
                              Text(
                                'Maksimum ompad: $_maxDetour minute',
                                style: GoogleFonts.inter(
                                  color: kText1,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Slider(
                                min: 0,
                                max: 120,
                                divisions: 24,
                                value: _maxDetour.toDouble().clamp(0.0, 120.0).toDouble(),
                                onChanged: (value) => setState(
                                  () => _maxDetour = value.round(),
                                ),
                              ),
                              SwitchListTile(
                                contentPadding: EdgeInsets.zero,
                                title: const Text(
                                  'Wys my in Saamry-aanbevelings',
                                  style: TextStyle(color: kText1),
                                ),
                                subtitle: const Text(
                                  'Skakel af as jy tydelik nie wil saamry nie.',
                                  style: TextStyle(color: kTextMuted, fontSize: 10.5),
                                ),
                                value: _active,
                                onChanged: (value) =>
                                    setState(() => _active = value),
                              ),
                              const SizedBox(height: 8),
                              GradientActionButton(
                                label: _saving ? 'Stoor...' : 'Stoor Voorkeure',
                                onTap: _saving ? () {} : _save,
                                height: 48,
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




class _FriendStateButton extends StatelessWidget {
  final String label;

  const _FriendStateButton({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 42,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: kBorder),
      ),
      child: Text(
        label,
        textAlign: TextAlign.center,
        style: GoogleFonts.inter(
          color: kTextMuted,
          fontSize: 10.5,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _RecommendationEmptyState extends StatelessWidget {
  final IconData icon;
  final String message;
  final String actionLabel;
  final VoidCallback onAction;

  const _RecommendationEmptyState({
    required this.icon,
    required this.message,
    required this.actionLabel,
    required this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Column(
        children: [
          Icon(icon, color: kTextMuted, size: 32),
          const SizedBox(height: 8),
          Text(
            message,
            textAlign: TextAlign.center,
            style: GoogleFonts.inter(color: kText2, fontSize: 11.5),
          ),
          const SizedBox(height: 8),
          TextButton(onPressed: onAction, child: Text(actionLabel)),
        ],
      ),
    );
  }
}
