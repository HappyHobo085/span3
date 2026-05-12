import 'package:flutter/material.dart';

import 'app_shared.dart';
import 'moon_api.dart';

// Home screen with two main panels.
class HomePage extends StatelessWidget {
  // Constructor.
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: loginPageBackground,
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: SizedBox(
              height: 240,
              width: double.infinity,
              child: Row(
                children: [
                  // Panel that opens access scanning page.
                  Expanded(
                    child: _OutlinedPanel(
                      text: 'Kampus Skandering',
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const LeftEmptyPage(),
                          ),
                        );
                      },
                    ),
                  ),
                  // Space between the two panels.
                  const SizedBox(width: 16),
                  // Panel that opens class scanning page.
                  Expanded(
                    child: _OutlinedPanel(
                      text: 'Klas Skandering',
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const RightEmptyPage(),
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// Reusable clickable panel used on home screen.
class _OutlinedPanel extends StatelessWidget {
  // Panel title text.
  final String text;
  // Tap action.
  final VoidCallback onTap;

  // Constructor.
  const _OutlinedPanel({
    required this.text,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    // Detect taps anywhere on the panel.
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          // Match screen background.
          color: loginPageBackground,
          // Neon border line.
          border: const Border.fromBorderSide(
            BorderSide(color: Color(0xFF7B61FF), width: 1.5),
          ),
          // Neon glow around panel.
          boxShadow: const [
            BoxShadow(
              blurRadius: 18,
              spreadRadius: 1,
              color: Color(0x4D7B61FF),
              offset: Offset(0, 0),
            ),
          ],
          borderRadius: BorderRadius.circular(2),
        ),
        child: Center(
          child: Text(
            text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ),
    );
  }
}

// Left scanning page.
class LeftEmptyPage extends StatelessWidget {
  // Constructor.
  const LeftEmptyPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: loginPageBackground,
      body: Stack(
        children: [
          // Fill page area.
          const SizedBox.expand(),
          // Top-left NFC panel.
          Align(
            alignment: Alignment.topLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: loginPageBackground,
                  border: const Border.fromBorderSide(
                    BorderSide(color: Color(0xFF7B61FF), width: 1.5),
                  ),
                  boxShadow: const [
                    BoxShadow(
                      blurRadius: 18,
                      spreadRadius: 1,
                      color: Color(0x4D7B61FF),
                      offset: Offset(0, 0),
                    ),
                  ],
                  borderRadius: BorderRadius.circular(2),
                ),
                child: const Center(
                  child: Text(
                    'NFC',
                    style: TextStyle(color: Colors.white),
                  ),
                ),
              ),
            ),
          ),
          // Center content panel.
          Align(
            alignment: Alignment.center,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Container(
                height: 220,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: loginPageBackground,
                  border: const Border.fromBorderSide(
                    BorderSide(color: Color(0xFF7B61FF), width: 1.5),
                  ),
                  boxShadow: const [
                    BoxShadow(
                      blurRadius: 18,
                      spreadRadius: 1,
                      color: Color(0x4D7B61FF),
                      offset: Offset(0, 0),
                    ),
                  ],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          ),
          // Bottom-left action button.
          Align(
            alignment: Alignment.bottomLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _BackButton(
                label: 'Skandeer in',
                onPressed: () {},
              ),
            ),
          ),
          // Bottom-right back button.
          Align(
            alignment: Alignment.bottomRight,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _BackButton(
                label: 'Terug',
                onPressed: () => Navigator.pop(context),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Right scanning page — klas-skandering; klaslys kom van backend ná NFC tik.
class RightEmptyPage extends StatefulWidget {
  const RightEmptyPage({super.key});

  @override
  State<RightEmptyPage> createState() => _RightEmptyPageState();
}

class _RightEmptyPageState extends State<RightEmptyPage> {
  String _dropdownValue = 'Opsie 1';

  /// Slegs ná gebruiker op NFC tik: haal data uit databasis via API.
  bool _nfcActivated = false;
  bool _loading = false;
  String? _errorMessage;
  List<LokasieDto> _lokasies = [];

  Future<void> _onNfcTapped() async {
    setState(() {
      _nfcActivated = true;
      _loading = true;
      _errorMessage = null;
    });

    try {
      final list = await MoonApi.fetchLokasies();
      if (!mounted) return;
      setState(() {
        _lokasies = list;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _errorMessage = e.toString();
        _lokasies = [];
      });
    }
  }

  Widget _buildCenterPanelBody() {
    if (!_nfcActivated) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Text(
          '(QR-kode, geldig vir 30 sekondes)',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.white),
        ),
      );
    }

    if (_loading) {
      return const Center(
        child: CircularProgressIndicator(color: Colors.white),
      );
    }

    if (_errorMessage != null) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: Text(
          _errorMessage!,
          textAlign: TextAlign.center,
          style: const TextStyle(color: Colors.white70, fontSize: 13),
        ),
      );
    }

    if (_lokasies.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Text(
          'Geen klasse in die databasis nie.\n'
          '(QR-kode, geldig vir 30 sekondes)',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.white),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.all(12),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              '(QR-kode, geldig vir 30 sekondes)',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white54, fontSize: 12),
            ),
            const SizedBox(height: 12),
            for (final LokasieDto l in _lokasies)
              Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l.naam,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    if (l.beskrywing != null &&
                        l.beskrywing!.trim().isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          l.beskrywing!,
                          style: const TextStyle(
                            color: Colors.white70,
                            fontSize: 14,
                          ),
                        ),
                      ),
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        'ID: ${l.id}${l.kampusId != null ? ' · Kampus: ${l.kampusId}' : ''}',
                        style: const TextStyle(
                          color: Colors.white54,
                          fontSize: 12,
                        ),
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: loginPageBackground,
      body: Stack(
        children: [
          const SizedBox.expand(),
          Align(
            alignment: Alignment.topLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Container(
                      decoration: BoxDecoration(
                        color: loginPageBackground,
                        border: const Border.fromBorderSide(
                          BorderSide(color: Color(0xFF7B61FF), width: 1.5),
                        ),
                        boxShadow: const [
                          BoxShadow(
                            blurRadius: 18,
                            spreadRadius: 1,
                            color: Color(0x4D7B61FF),
                            offset: Offset(0, 0),
                          ),
                        ],
                        borderRadius: BorderRadius.circular(2),
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<String>(
                          value: _dropdownValue,
                          dropdownColor: loginPageBackground,
                          isExpanded: true,
                          items: const [
                            DropdownMenuItem(
                              value: 'Opsie 1',
                              child: Text(
                                'Opsie 1',
                                style: TextStyle(color: Colors.white),
                              ),
                            ),
                            DropdownMenuItem(
                              value: 'Opsie 2',
                              child: Text(
                                'Opsie 2',
                                style: TextStyle(color: Colors.white),
                              ),
                            ),
                          ],
                          onChanged: (v) {
                            if (v != null) {
                              setState(() => _dropdownValue = v);
                            }
                          },
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: _onNfcTapped,
                      borderRadius: BorderRadius.circular(2),
                      child: Container(
                        width: 72,
                        height: 72,
                        decoration: BoxDecoration(
                          color: loginPageBackground,
                          border: const Border.fromBorderSide(
                            BorderSide(color: Color(0xFF7B61FF), width: 1.5),
                          ),
                          boxShadow: const [
                            BoxShadow(
                              blurRadius: 18,
                              spreadRadius: 1,
                              color: Color(0x4D7B61FF),
                              offset: Offset(0, 0),
                            ),
                          ],
                          borderRadius: BorderRadius.circular(2),
                        ),
                        child: const Center(
                          child: Text(
                            'NFC',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          Align(
            alignment: Alignment.center,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Container(
                height: 220,
                width: double.infinity,
                decoration: BoxDecoration(
                  color: loginPageBackground,
                  border: const Border.fromBorderSide(
                    BorderSide(color: Color(0xFF7B61FF), width: 1.5),
                  ),
                  boxShadow: const [
                    BoxShadow(
                      blurRadius: 18,
                      spreadRadius: 1,
                      color: Color(0x4D7B61FF),
                      offset: Offset(0, 0),
                    ),
                  ],
                  borderRadius: BorderRadius.circular(2),
                ),
                child: _buildCenterPanelBody(),
              ),
            ),
          ),
          Align(
            alignment: Alignment.bottomLeft,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: _BackButton(
                label: 'Terug',
                onPressed: () => Navigator.pop(context),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Reusable back/action button wrapper.
class _BackButton extends StatelessWidget {
  // Button label text.
  final String label;
  // Function to call when pressed.
  final VoidCallback onPressed;

  // Constructor.
  const _BackButton({
    required this.label,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    // Reuse the gradient neon button style.
    return GradientActionButton(
      label: label,
      onTap: onPressed,
      width: 160,
      height: 45,
    );
  }
}
