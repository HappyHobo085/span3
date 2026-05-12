import 'package:flutter/material.dart';

/// Gemeenskaplike kleure vir student-/personeel-skerme (los van main.dart om sirkulêre imports te vermy).
const Color loginBrown = Color(0xFF935E28);
const Color loginDarkBlue = Color(0xFF0E1E3B);
const Color loginPageBackground = Color(0xFF0D132C);

/// Herbruikbare gradient-knoppie (neon-styl).
class GradientActionButton extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  final double width;
  final double height;

  const GradientActionButton({
    super.key,
    required this.label,
    required this.onTap,
    this.width = 324.65,
    this.height = 45,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      splashColor: Colors.transparent,
      focusColor: Colors.transparent,
      hoverColor: Colors.transparent,
      highlightColor: Colors.transparent,
      onTap: onTap,
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          boxShadow: const [
            BoxShadow(
              blurRadius: 25,
              color: Color(0xA87B61FF),
              offset: Offset(0, 2),
              spreadRadius: 2,
            ),
          ],
          gradient: const LinearGradient(
            colors: [Color(0xFF7B61FF), Color(0xFF00C2FF)],
            stops: [0, 1],
            begin: AlignmentDirectional(0, -1),
            end: AlignmentDirectional(0, 1),
          ),
          borderRadius: BorderRadius.circular(15),
          border: Border.all(color: const Color(0xFF7B61FF)),
        ),
        alignment: const AlignmentDirectional(0, 0),
        child: Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }
}
