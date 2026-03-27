import 'package:flutter/material.dart';
import 'main.dart';

class SekuriteitswagHomePage extends StatelessWidget {
  const SekuriteitswagHomePage({super.key});

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
                  // Left panel
                  Expanded(
                    child: _OutlinedPanel(
                      text: 'Skandeer Akademia lede',
                      onTap: () {
                        // For now just redirect to a placeholder page
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const _PlaceholderPage(title: 'Skandeer Akademia lede'),
                          ),
                        );
                      },
                    ),
                  ),
                  const SizedBox(width: 16),
                  // Right panel
                  Expanded(
                    child: _OutlinedPanel(
                      text: 'Skandeer Besoeker',
                      onTap: () {
                        // For now just redirect to a placeholder page
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (_) => const _PlaceholderPage(title: 'Skandeer Besoeker'),
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

// Reusable clickable panel (consistent with other pages)
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

// Simple placeholder page to give you navigation before we detail these pages.
class _PlaceholderPage extends StatelessWidget {
  final String title;
  const _PlaceholderPage({required this.title});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: loginPageBackground,
      appBar: AppBar(
        title: Text(title, style: const TextStyle(color: Colors.white)),
        backgroundColor: loginDarkBlue,
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: Center(
        child: Text(
          '$title - Bladsy is tans onder konstruksie',
          textAlign: TextAlign.center,
          style: const TextStyle(color: Colors.white, fontSize: 18),
        ),
      ),
    );
  }
}
