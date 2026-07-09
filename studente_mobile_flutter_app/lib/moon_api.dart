import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';


/// =========================
/// Kampus DTO
/// =========================

class KampusDto {
  final int? kampusId;
  final String naam;

  KampusDto({
    required this.kampusId,
    required this.naam,
  });

  factory KampusDto.fromJson(Map<String, dynamic> json) {
    return KampusDto(
      kampusId: json['Kampus_ID'] as int?,
      naam: json['KAM_Naam'] as String,
    );
  }
}



/// =========================
/// Koshuis DTO
/// =========================

class KoshuisDto {
  final int? koshuisId;
  final String naam;

  KoshuisDto({
    required this.koshuisId,
    required this.naam,
  });

  factory KoshuisDto.fromJson(Map<String, dynamic> json) {
    return KoshuisDto(
      koshuisId: (json['Koshuis_ID'] ??
              json['koshuis_id'] ??
              json['id']) as int?,
      naam: (json['KOS_Naam'] ??
              json['naam'] ??
              json['name'] ??
              'Onbekende koshuis')
          .toString(),
    );
  }
}


/// =========================
/// Lokasie DTO
/// =========================

class LokasieDto {
  final int id;
  final String naam;
  final String? beskrywing;
  final int? kampusId;
  final String? nfcUid;

  LokasieDto({
    required this.id,
    required this.naam,
    this.beskrywing,
    this.kampusId,
    this.nfcUid,
  });

  factory LokasieDto.fromJson(Map<String, dynamic> json) {
    return LokasieDto(
      id: json['Lokasie_ID'] as int,
      naam: json['LOK_Naam'] as String,
      beskrywing: json['LOK_Tipe'] as String?,
      kampusId: json['Kampus_ID'] as int?,
      nfcUid: json['NFC_UID'] as String?,
    );
  }
}

class StudentSearchDto {
  final int gebruikerId;
  final String studentNommer;
  final String naam;
  final String van;
  final String? fotoUrl;

  StudentSearchDto({
    required this.gebruikerId,
    required this.studentNommer,
    required this.naam,
    required this.van,
    this.fotoUrl,
  });

  factory StudentSearchDto.fromJson(Map<String, dynamic> json) {
    return StudentSearchDto(
      gebruikerId: json['gebruiker_id'] as int,
      studentNommer: json['student_nommer']?.toString() ?? '',
      naam: json['naam']?.toString() ?? '',
      van: json['van']?.toString() ?? '',
      fotoUrl: json['foto_url']?.toString(),
    );
  }

  String get fullName => '$naam $van';
}


class WagteProfileScanDto {
  final int gebruikerId;
  final String naam;
  final String van;
  final String idNommer;
  final String? fotoUrl;
  final String voorgesteldeRigting;

  WagteProfileScanDto({
    required this.gebruikerId,
    required this.naam,
    required this.van,
    required this.idNommer,
    this.fotoUrl,
    required this.voorgesteldeRigting,
  });
}


/// =========================
/// Moon API
/// =========================

class MoonApi {
  MoonApi._();

  /// Verander na jou backend IP
  static String baseUrl = "http://happyhobo-pc.tail251156.ts.net:8000";

  /// JWT token indien benodig
  static String? bearerToken;
  static Future<Map<String, dynamic>> login({
    required String email,
    required String password,
    }) async {
      final uri = Uri.parse('$baseUrl/token');

      final response = await http.post(
        uri,
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: {
          'grant_type': 'password',
          'username': email,
          'password': password,
          'scope': '',
          'client_id': '',
          'client_secret': '',
        },
      );

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200 || decoded['sukses'] != true) {
      throw Exception(
        decoded['fout'] ?? decoded['detail'] ?? 'Login het misluk',
      );
    }

    final token = decoded['data']['access_token'] as String;
    bearerToken = token;

    return Map<String, dynamic>.from(decoded['data']);
  }
  /// -------------------------
  /// Kampusse
  /// -------------------------

  static Future<List<KampusDto>> fetchKampusse() async {
    final uri = Uri.parse('$baseUrl/kampusse');

    final headers = <String, String>{
      'Accept': 'application/json',
      if (bearerToken != null && bearerToken!.trim().isNotEmpty)
        'Authorization': 'Bearer ${bearerToken!.trim()}',
    };

    final response = await http.get(uri, headers: headers);

    if (response.statusCode != 200) {
      throw Exception(
        'Bedienerfout HTTP ${response.statusCode}: ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);

    if (decoded['sukses'] != true) {
      throw Exception(
        decoded['fout']?.toString() ?? 'Kon nie kampusse laai nie',
      );
    }

    final raw = decoded['data'];

    if (raw == null) return [];

    return (raw as List)
        .map((e) => KampusDto.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }

  /// -------------------------
  /// Lokasies
  /// -------------------------
  static Future<Map<String, dynamic>> studentScanKlas({
    required String nfcUid,
    required String rigting,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/student/scan-klas'),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Bearer ${bearerToken!}',
      },
      body: jsonEncode({
        'nfc_uid': nfcUid,
        'rigting': rigting,
      }),
    );

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200 ||
        decoded['sukses'] != true) {
      throw Exception(
        decoded['detail'] ??
            decoded['fout'] ??
            'Scan het misluk',
      );
    }

    return Map<String, dynamic>.from(decoded['data']);
  }


  static Future<List<LokasieDto>> fetchLokasies() async {
    final uri = Uri.parse('$baseUrl/lokasies');

    final headers = <String, String>{
      'Accept': 'application/json',
      if (bearerToken != null && bearerToken!.trim().isNotEmpty)
        'Authorization': 'Bearer ${bearerToken!.trim()}',
    };

    final response = await http.get(uri, headers: headers);

    if (response.statusCode == 401 || response.statusCode == 403) {
      throw Exception(
        'Geen toegang tot lokasies nie. Login asseblief weer.',
      );
    }

    if (response.statusCode != 200) {
      throw Exception(
        'Bedienerfout HTTP ${response.statusCode}: ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);
    
    if (decoded['sukses'] != true) {
      throw Exception(
        decoded['fout']?.toString() ?? 'Kon nie lokasies laai nie',
      );
    }

    final raw = decoded['data'];

    if (raw == null) return [];

    return (raw as List)
        .map((e) => LokasieDto.fromJson(Map<String, dynamic>.from(e)))
        .toList();
  }


  static Future<List<StudentSearchDto>> searchStudents(String query) async {
  final clean = query.trim();

  if (clean.length < 2) return [];

  final response = await http.get(
    Uri.parse('$baseUrl/studente/search?q=${Uri.encodeQueryComponent(clean)}'),
    headers: {
      'Accept': 'application/json',
      if (bearerToken != null && bearerToken!.trim().isNotEmpty)
        'Authorization': 'Bearer ${bearerToken!.trim()}',
    },
  );

  final decoded = jsonDecode(response.body);

  if (response.statusCode != 200 || decoded['sukses'] != true) {
    throw Exception(
      decoded['fout'] ?? decoded['detail'] ?? 'Kon nie studente soek nie',
    );
  }

  final raw = decoded['data'];

  if (raw == null) return [];

  return (raw as List)
      .map((e) => StudentSearchDto.fromJson(Map<String, dynamic>.from(e)))
      .toList();
}


static Future<Map<String, dynamic>> fetchLiveDashboard() async {
  final response = await http.get(
    Uri.parse('$baseUrl/dashboard/live'),
    headers: {
      'Accept': 'application/json',
      if (bearerToken != null)
        'Authorization': 'Bearer $bearerToken',
    },
  );

  final decoded = jsonDecode(response.body);

  if (response.statusCode != 200 || decoded['sukses'] != true) {
    throw Exception(
      decoded['fout'] ?? decoded['detail'] ?? 'Dashboard kon nie laai nie',
    );
  }

  return Map<String, dynamic>.from(decoded['data']);
}

  /// -------------------------
  /// Wagte Student Scan
  /// -------------------------

  static Future<Map<String, dynamic>> wagteStudentScan({
    required String studentNomOrId,
    required int lokasieId,
    required String rigting,
    required String metode,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/wagte/student/scan'),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (bearerToken != null && bearerToken!.trim().isNotEmpty)
          'Authorization': 'Bearer ${bearerToken!.trim()}',
      },
      body: jsonEncode({
        'student_nom_or_id': studentNomOrId,
        'lokasie_id': lokasieId,
        'rigting': rigting,
        'metode': metode,
      }),
    );

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        decoded['detail'] ??
            decoded['fout'] ??
            'Student skandering het misluk',
      );
    }

    if (decoded['sukses'] != true) {
      throw Exception(
        decoded['fout'] ?? 'Student skandering het misluk',
      );
    }

    return Map<String, dynamic>.from(decoded['data']);
  }

  static Map<String, dynamic>? myProfile;

  static Future<Map<String, dynamic>> getMyProfile() async {
    final response = await http.get(
      Uri.parse('$baseUrl/me'),
      headers: {
        'Accept': 'application/json',
        if (bearerToken != null && bearerToken!.trim().isNotEmpty)
          'Authorization': 'Bearer ${bearerToken!.trim()}',
      },
    );

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200 || decoded['sukses'] != true) {
      throw Exception(
        decoded['fout'] ?? decoded['detail'] ?? 'Kon nie profiel laai nie',
      );
    }

    myProfile = Map<String, dynamic>.from(decoded['data']);
    return myProfile!;
  }

  static String? get myStudentNommer {
    return myProfile?['student_nommer']?.toString();
  }

  static Future<String> uploadMyProfilePhoto(File file) async {
    final uri = Uri.parse('$baseUrl/me/foto');

    final request = http.MultipartRequest('POST', uri);

    if (bearerToken != null && bearerToken!.trim().isNotEmpty) {
      request.headers['Authorization'] = 'Bearer ${bearerToken!.trim()}';
    }

    final ext = file.path.split('.').last.toLowerCase();

  String contentType = 'image/jpeg';

  if (ext == 'png') {
    contentType = 'image/png';
  } else if (ext == 'webp') {
    contentType = 'image/webp';
  }

  request.files.add(
    await http.MultipartFile.fromPath(
      'file',
      file.path,
      contentType: MediaType.parse(contentType),
    ),
  );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    print('UPLOAD STATUS = ${response.statusCode}');
    print('UPLOAD BODY = ${response.body}');

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200 || decoded['sukses'] != true) {
      throw Exception(
        decoded['fout'] ?? decoded['detail'] ?? 'Foto upload het misluk',
      );
    }

    final fotoUrl = decoded['data']['foto_url'].toString();

    if (myProfile != null) {
      myProfile!['foto_url'] = fotoUrl;
    }

    return fotoUrl;
  }

  static void logout() {
    bearerToken = null;
    myProfile = null;
  }


  static Future<List<KampusDto>> fetchWagteKampusse() async {
  final response = await http.get(
    Uri.parse('$baseUrl/wagte/kampusse'),
    headers: {
      'Accept': 'application/json',
      if (bearerToken != null && bearerToken!.trim().isNotEmpty)
        'Authorization': 'Bearer ${bearerToken!.trim()}',
    },
  );

  final decoded = jsonDecode(response.body);

  if (response.statusCode != 200 || decoded['sukses'] != true) {
    throw Exception(
      decoded['fout'] ?? decoded['detail'] ?? 'Kon nie kampusse laai nie',
    );
  }

  final raw = decoded['data'];

  if (raw == null) return [];

  return (raw as List).map((e) {
    final item = Map<String, dynamic>.from(e);

    return KampusDto(
      kampusId: item['kampus_id'] as int?,
      naam: item['naam']?.toString() ?? '',
    );
  }).toList();
}

  static Future<Map<String, dynamic>> fetchDashboard() async {
  final response = await http.get(
    Uri.parse('$baseUrl/dashboard'),
    headers: {
      'Accept': 'application/json',
      if (bearerToken != null && bearerToken!.trim().isNotEmpty)
        'Authorization': 'Bearer ${bearerToken!.trim()}',
    },
  );

  final decoded = jsonDecode(response.body);

  if (response.statusCode != 200 || decoded['sukses'] != true) {
    throw Exception(
      decoded['fout'] ?? decoded['detail'] ?? 'Kon nie dashboard laai nie',
    );
  }

  return Map<String, dynamic>.from(decoded['data']);
  }

  static Future<WagteProfileScanDto> wagteProfileScan(
    String scanKode,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/wagte/profile/scan'),
      headers: {
        "Content-Type": "application/json",
        if (bearerToken != null)
          "Authorization": "Bearer $bearerToken",
      },
      body: jsonEncode({
        "scan_kode": scanKode,
      }),
    );

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200 || decoded["sukses"] != true) {
      throw Exception(decoded["fout"] ?? decoded["detail"] ?? "Kon nie profiel kry nie");
    }

    final d = decoded["data"];

    return WagteProfileScanDto(
      gebruikerId: d["gebruiker_id"],
      naam: d["naam"],
      van: d["van"],
      idNommer: d["id_nommer"],
      fotoUrl: d["foto_url"],
      voorgesteldeRigting: d["voorgestelde_rigting"] ?? "IN",
    );
  }

  static Future<Map<String, dynamic>> wagteProfileVerify({
    required int gebruikerId,
    required int kampusId,
    required String rigting,
    required String metode,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/wagte/profile/verify'),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (bearerToken != null && bearerToken!.trim().isNotEmpty)
          'Authorization': 'Bearer ${bearerToken!.trim()}',
      },
      body: jsonEncode({
        'gebruiker_id': gebruikerId,
        'kampus_id': kampusId,
        'rigting': rigting,
        'metode': metode,
      }),
    );

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200 || decoded['sukses'] != true) {
      throw Exception(
        decoded['fout'] ?? decoded['detail'] ?? 'Verify het misluk',
      );
    }

    return Map<String, dynamic>.from(decoded['data']);
  }
  

  static Future<List<KampusDto>> fetchOpsigterKampusse() async {
    final response = await http.get(
      Uri.parse('$baseUrl/wagte/kampusse'),
      headers: {
        'Accept': 'application/json',
        if (bearerToken != null && bearerToken!.trim().isNotEmpty)
          'Authorization': 'Bearer ${bearerToken!.trim()}',
      },
    );

    print('KAMPUS LYS URL = $baseUrl/wagte/kampusse');
    print('KAMPUS LYS STATUS = ${response.statusCode}');
    print('KAMPUS LYS BODY = ${response.body}');

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200 || decoded['sukses'] != true) {
      throw Exception(
        decoded['fout'] ?? decoded['detail'] ?? 'Kon nie kampusse laai nie',
      );
    }

    final raw = decoded['data'];
    if (raw == null) return [];

    return (raw as List).map((e) {
      final item = Map<String, dynamic>.from(e as Map);

      return KampusDto(
        kampusId: item['kampus_id'] as int?,
        naam: item['naam']?.toString() ?? '',
      );
    }).toList();
  }

  static Future<Map<String, dynamic>> fetchKampusStatus(int kampusId) async {
    final url = '$baseUrl/kampusse/$kampusId/status';

    final response = await http.get(
      Uri.parse(url),
      headers: {
        'Accept': 'application/json',
        if (bearerToken != null && bearerToken!.trim().isNotEmpty)
          'Authorization': 'Bearer ${bearerToken!.trim()}',
      },
    );

    print('KAMPUS STATUS URL = $url');
    print('KAMPUS STATUS CODE = ${response.statusCode}');
    print('KAMPUS STATUS BODY = ${response.body}');

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200 || decoded['sukses'] != true) {
      throw Exception(
        decoded['fout'] ?? decoded['detail'] ?? 'Kon nie kampus status laai nie',
      );
    }

    return Map<String, dynamic>.from(decoded['data']);
  }


  static Future<List<KoshuisDto>> fetchKoshuise() async {
    final candidates = [
      '$baseUrl/koshuise',
      '$baseUrl/koshuis',
    ];

    http.Response? lastResponse;

    for (final url in candidates) {
      final response = await http.get(
        Uri.parse(url),
        headers: {
          'Accept': 'application/json',
          if (bearerToken != null && bearerToken!.trim().isNotEmpty)
            'Authorization': 'Bearer ${bearerToken!.trim()}',
        },
      );

      print('KOSHUIS LYS URL = $url');
      print('KOSHUIS LYS STATUS = ${response.statusCode}');
      print('KOSHUIS LYS BODY = ${response.body}');

      lastResponse = response;

      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body);

        if (decoded['sukses'] == true) {
          final raw = decoded['data'];
          if (raw == null) return [];

          return (raw as List)
              .map((e) => KoshuisDto.fromJson(Map<String, dynamic>.from(e as Map)))
              .toList();
        }
      }
    }

    if (lastResponse != null) {
      final decoded = jsonDecode(lastResponse.body);
      throw Exception(
        decoded['fout'] ?? decoded['detail'] ?? 'Kon nie koshuise laai nie',
      );
    }

    throw Exception('Kon nie koshuise laai nie');
  }

  static Future<Map<String, dynamic>> fetchKoshuisStatus(int koshuisId) async {
    final url = '$baseUrl/koshuise/$koshuisId/status';

    final response = await http.get(
      Uri.parse(url),
      headers: {
        'Accept': 'application/json',
        if (bearerToken != null && bearerToken!.trim().isNotEmpty)
          'Authorization': 'Bearer ${bearerToken!.trim()}',
      },
    );

    print('KOSHUIS STATUS URL = $url');
    print('KOSHUIS STATUS CODE = ${response.statusCode}');
    print('KOSHUIS STATUS BODY = ${response.body}');

    final decoded = jsonDecode(response.body);

    if (response.statusCode != 200 || decoded['sukses'] != true) {
      throw Exception(
        decoded['fout'] ?? decoded['detail'] ?? 'Kon nie koshuis status laai nie',
      );
    }

    return Map<String, dynamic>.from(decoded['data']);
  }

}



