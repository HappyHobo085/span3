import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_shared.dart';
import 'moon_api.dart';
import 'dart:io';
import 'package:image_picker/image_picker.dart';
import 'main.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  bool _loading = true;
  Map<String, dynamic>? _profile;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final data = await MoonApi.getMyProfile();

      if (!mounted) return;

      setState(() {
        _profile = data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

 Future<void> _changePhoto() async {
  final source = await showModalBottomSheet<ImageSource>(
    context: context,
    backgroundColor: kBg,
    builder: (context) {
      return SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt, color: kAccent),
              title: Text('Neem foto', style: GoogleFonts.inter(color: kText1)),
              onTap: () => Navigator.pop(context, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library, color: kAccent),
              title: Text('Kies uit gallery', style: GoogleFonts.inter(color: kText1)),
              onTap: () => Navigator.pop(context, ImageSource.gallery),
            ),
          ],
        ),
      );
    },
  );

  if (source == null) return;

  try {
    final picker = ImagePicker();

    final picked = await picker.pickImage(
      source: source,
      imageQuality: 75,
    );

    if (picked == null) return;

    setState(() => _loading = true);

    await MoonApi.uploadMyProfilePhoto(File(picked.path));

    final refreshed = await MoonApi.getMyProfile();

    if (!mounted) return;

    setState(() {
      _profile = refreshed;
      _loading = false;
    });
  } catch (e) {
    if (!mounted) return;

    setState(() => _loading = false);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: Colors.red,
        content: Text(
          'Foto fout: $e',
          style: const TextStyle(color: Colors.white),
        ),
      ),
    );
  }
}

  static const _numberKeys = [
    'student_nommer',
    'personeel_nommer',
    'opsigter_nommer',
    'wag_nommer',
  ];

  String? _numberKeyForRole(String rol) {
    switch (rol) {
      case 'Student':
        return 'student_nommer';
      case 'Personeel':
        return 'personeel_nommer';
      case 'Kampus_Opsigter':
        return 'opsigter_nommer';
      case 'Sekuriteit_Wag':
        return 'wag_nommer';
      default:
        return null;
    }
  }

  /// Kies die nommersleutel wat by die gebruiker se rol pas; val terug op die
  /// vaste volgorde wanneer die rol-sleutel ontbreek of leeg is.
  String? _chosenNumberKey(Map<String, dynamic> p) {
    final rolKey = _numberKeyForRole(p['rol']?.toString() ?? '');

    if (rolKey != null && p[rolKey] != null) {
      return rolKey;
    }

    for (final key in _numberKeys) {
      if (p[key] != null) {
        return key;
      }
    }

    return null;
  }

  String _displayNumber(Map<String, dynamic> p) {
    final key = _chosenNumberKey(p);

    if (key == null) return 'Nie beskikbaar';

    return p[key]?.toString() ?? 'Nie beskikbaar';
  }

  String _numberLabel(Map<String, dynamic> p) {
    // Bly konsekwent met die sleutel wat gekies is; sonder enige nommer val
    // dit terug op die etiket wat by die rol pas.
    final key = _chosenNumberKey(p) ??
        _numberKeyForRole(p['rol']?.toString() ?? '');

    switch (key) {
      case 'student_nommer':
        return 'Studentnommer';
      case 'personeel_nommer':
        return 'Personeelnommer';
      case 'opsigter_nommer':
        return 'Opsigternommer';
      case 'wag_nommer':
        return 'Wagnommer';
      default:
        return 'Nommer';
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
              title: 'Profiel',
              subtitle: 'My besonderhede',
            ),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? Center(
                          child: Text(
                            _error!,
                            style: GoogleFonts.inter(color: Colors.red),
                          ),
                        )
                      : _buildProfile(_profile!),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProfile(Map<String, dynamic> p) {
    final naam = p['naam']?.toString() ?? '';
    final van = p['van']?.toString() ?? '';
    final rol = p['rol']?.toString() ?? '';
    final fotoUrl = p['foto_url']?.toString() ?? '';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          GlassCard(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                if (fotoUrl.isNotEmpty)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(60),
                    child: Image.network(
                      '${MoonApi.baseUrl}$fotoUrl?v=${DateTime.now().millisecondsSinceEpoch}',
                      width: 110,
                      height: 110,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const Icon(
                        Icons.person,
                        color: kTextMuted,
                        size: 90,
                      ),
                    ),
                  )
                else
                  const Icon(
                    Icons.person,
                    color: kTextMuted,
                    size: 95,
                  ),

                const SizedBox(height: 14),

                Text(
                  '$naam $van',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    color: kText1,
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  ),
                ),

                const SizedBox(height: 4),

                Text(
                  rol,
                  style: GoogleFonts.inter(
                    color: kAccent,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          GlassCard(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                _InfoRow(label: _numberLabel(p), value: _displayNumber(p)),
                const _ThinDivider(),
                _InfoRow(label: 'E-pos', value: p['epos']?.toString() ?? ''),
                const _ThinDivider(),
                _InfoRow(label: 'Selfoon', value: p['selfoon']?.toString() ?? ''),
                const _ThinDivider(),
                _InfoRow(label: 'Status', value: p['status']?.toString() ?? ''),
                const _ThinDivider(),
                _InfoRow(
                  label: 'Kampus',
                  value: p['kampus']?.toString() ?? 'Nie gekoppel nie',
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          GradientActionButton(
            label: 'Verander Foto',
            onTap: _changePhoto,
            height: 48,
          ),

          const SizedBox(height: 12),

          OutlineActionButton(
            label: 'Logout',
            onTap: () {
              MoonApi.logout();

              Navigator.of(context, rootNavigator: true).pushAndRemoveUntil(
                MaterialPageRoute(builder: (_) => const LoginPage()),
                (route) => false,
              );
            },
            height: 48,
          ),
        ],
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({
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
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value.isEmpty ? 'Nie beskikbaar' : value,
              textAlign: TextAlign.right,
              style: GoogleFonts.inter(
                color: kText1,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ThinDivider extends StatelessWidget {
  const _ThinDivider();

  @override
  Widget build(BuildContext context) {
    return const Divider(
      color: Color(0x0AFFFFFF),
      height: 1,
    );
  }
}