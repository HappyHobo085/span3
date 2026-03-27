import 'package:flutter/material.dart';
import 'main.dart';

class PersoneelHomePage extends StatelessWidget {
  const PersoneelHomePage({super.key});

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
                  // Left panel = Kampus Inskandering
                  Expanded(
                    child: _OutlinedPanel(
                      text: 'Kampus Inskandering',
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const PersoneelKampusInskanderingPage(),
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(width: 16),
                  // Right panel = Klas Bywoning
                  Expanded(
                    child: _OutlinedPanel(
                      text: 'Klas Bywoning',
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const KlasBywoningPage(),
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

// Reusable clickable panel 
class _OutlinedPanel extends StatelessWidget {
  final String text;
  final VoidCallback onTap;

  const _OutlinedPanel({
    required this.text,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
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

// Reusable back/action button wrapper.
class _BackButton extends StatelessWidget {
  final String label;
  final VoidCallback onPressed;

  const _BackButton({
    required this.label,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return GradientActionButton(
      label: label,
      onTap: onPressed,
      width: 160,
      height: 45,
    );
  }
}

// Left scanning page for Personeel (same layout as student's LeftEmptyPage)
class PersoneelKampusInskanderingPage extends StatelessWidget {
  const PersoneelKampusInskanderingPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: loginPageBackground,
      body: Stack(
        children: [
          const SizedBox.expand(),
          // Top-left NFC panel
          Align(
            alignment: Alignment.topLeft,
            child: Padding(
              padding: const EdgeInsets.only(top: 60, left: 16), // adjust top padding slightly to miss safe area visually
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
          // Center content panel
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
          // Bottom-left action button
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
          // Bottom-right back button
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

// Klas Bywoning page for Personeel
class KlasBywoningPage extends StatelessWidget {
  const KlasBywoningPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: loginPageBackground,
      body: Stack(
        children: [
          // Fill page area
          const SizedBox.expand(),

          // 5.1 Dropdown box slightly below the top left
          Positioned(
            top: 60, // slightly below top
            left: 16,
            child: _buildNeonDropdown('Opsie 1'),
          ),

          // Center area containing the center panel (5.2) and Filtreer section (5.3)
          Align(
            alignment: Alignment.center,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24),
              child: Column(
                mainAxisSize: MainAxisSize.min, // Wrap content height-wise
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 5.3 dropdown box slightly above the panel on the left side labeled "Filtreer" and a button "Verfris" slightly right
                  Row(
                    children: [
                      _buildNeonDropdown('Filtreer'),
                      const SizedBox(width: 16),
                      GradientActionButton(
                        label: 'Verfris',
                        width: 140, // width to fit Verfris comfortably
                        height: 48,
                        onTap: () {},
                      ),
                    ],
                  ),
                  const SizedBox(height: 16), // space between filtreer bar and center panel

                  // 5.2 Panel in the center of the screen
                  Container(
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
                    child: const Center(
                      child: Text(
                        '(Klas Bywoning Inligting)',
                        style: TextStyle(color: Colors.white),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // 5.4 Bottom right Terug button
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

  // helper widget to build neon dropdown boxes
  Widget _buildNeonDropdown(String value) {
    return Container(
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
          value: value,
          dropdownColor: loginPageBackground,
          items: [
            DropdownMenuItem(
              value: value,
              child: Text(
                value,
                style: const TextStyle(color: Colors.white),
              ),
            ),
            const DropdownMenuItem(
              value: 'Ander',
              child: Text(
                'Ander',
                style: TextStyle(color: Colors.white),
              ),
            ),
          ],
          onChanged: (_) {},
        ),
      ),
    );
  }
}
