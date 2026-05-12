import 'package:flutter/material.dart';
import 'app_shared.dart';

class OpsigterHomePage extends StatelessWidget {
  const OpsigterHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: loginPageBackground,
      body: SafeArea(
        child: Padding(
          // Padding gives that "slightly underneath top" and "slightly above bottom" feel
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 32.0),
          child: Column(
            children: [
              // 1 & 2: Top panels
              Expanded(
                child: Row(
                  children: [
                    Expanded(
                      child: _OutlinedPanel(
                        text: 'Noodgevalle',
                        onTap: () {
                          // Placeholder for future navigation
                        },
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _OutlinedPanel(
                        text: 'Koshuis oorsig',
                        onTap: () {},
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              
              // 3 & 4: Center panels
              Expanded(
                child: Row(
                  children: [
                    Expanded(
                      child: _OutlinedPanel(
                        text: 'Kampus oorsig',
                        onTap: () {},
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: _OutlinedPanel(
                        text: 'Funksies oorsig',
                        onTap: () {},
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              
              // 5: Bottom panel
              Expanded(
                child: Row(
                  children: [
                    Expanded(
                      child: _OutlinedPanel(
                        text: 'Parkeer spasie',
                        onTap: () {},
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// Reusable clickable panel (matching the styles set up in other files)
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
