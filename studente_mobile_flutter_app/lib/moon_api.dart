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


/// =========================
/// Saamry DTOs
/// =========================

class SaamryUserDto {
  final int gebruikerId;
  final String naam;
  final String van;
  final String volleNaam;
  final String nommer;
  final String rol;
  final String? fotoUrl;
  final String? selfoon;
  final String? epos;
  final String? vriendskapStatus;
  final int? vriendskapId;

  SaamryUserDto({
    required this.gebruikerId,
    required this.naam,
    required this.van,
    required this.volleNaam,
    required this.nommer,
    required this.rol,
    this.fotoUrl,
    this.selfoon,
    this.epos,
    this.vriendskapStatus,
    this.vriendskapId,
  });

  factory SaamryUserDto.fromJson(Map<String, dynamic> json) {
    return SaamryUserDto(
      gebruikerId: (json['gebruiker_id'] as num).toInt(),
      naam: json['naam']?.toString() ?? '',
      van: json['van']?.toString() ?? '',
      volleNaam: json['volle_naam']?.toString() ??
          '${json['naam'] ?? ''} ${json['van'] ?? ''}'.trim(),
      nommer: json['nommer']?.toString() ?? '',
      rol: json['rol']?.toString() ?? '',
      fotoUrl: json['foto_url']?.toString(),
      selfoon: json['selfoon']?.toString(),
      epos: json['epos']?.toString(),
      vriendskapStatus: json['vriendskap_status']?.toString(),
      vriendskapId: json['vriendskap_id'] == null
          ? null
          : (json['vriendskap_id'] as num).toInt(),
    );
  }
}

class SaamryFriendItemDto {
  final int vriendskapId;
  final String status;
  final SaamryUserDto gebruiker;

  SaamryFriendItemDto({
    required this.vriendskapId,
    required this.status,
    required this.gebruiker,
  });

  factory SaamryFriendItemDto.fromJson(Map<String, dynamic> json) {
    return SaamryFriendItemDto(
      vriendskapId: (json['vriendskap_id'] as num).toInt(),
      status: json['status']?.toString() ?? '',
      gebruiker: SaamryUserDto.fromJson(
        Map<String, dynamic>.from(json['gebruiker'] as Map),
      ),
    );
  }
}

class SaamryGroupMemberDto {
  final String status;
  final bool isBestuurder;
  final SaamryUserDto gebruiker;

  SaamryGroupMemberDto({
    required this.status,
    required this.isBestuurder,
    required this.gebruiker,
  });

  factory SaamryGroupMemberDto.fromJson(Map<String, dynamic> json) {
    return SaamryGroupMemberDto(
      status: json['status']?.toString() ?? '',
      isBestuurder: json['is_bestuurder'] == true,
      gebruiker: SaamryUserDto.fromJson(
        Map<String, dynamic>.from(json['gebruiker'] as Map),
      ),
    );
  }
}

class SaamryGroupDto {
  final int groepId;
  final String naam;
  final String vertrekpunt;
  final String bestemming;
  final DateTime vertrekTyd;
  final int sitplekke;
  final int beskikbareSitplekke;
  final String status;
  final bool isBestuurder;
  final String? myStatus;
  final SaamryUserDto bestuurder;
  final List<SaamryGroupMemberDto> lede;

  SaamryGroupDto({
    required this.groepId,
    required this.naam,
    required this.vertrekpunt,
    required this.bestemming,
    required this.vertrekTyd,
    required this.sitplekke,
    required this.beskikbareSitplekke,
    required this.status,
    required this.isBestuurder,
    required this.myStatus,
    required this.bestuurder,
    required this.lede,
  });

  factory SaamryGroupDto.fromJson(Map<String, dynamic> json) {
    final rawMembers = (json['lede'] as List?) ?? const [];
    return SaamryGroupDto(
      groepId: (json['groep_id'] as num).toInt(),
      naam: json['naam']?.toString() ?? '',
      vertrekpunt: json['vertrekpunt']?.toString() ?? '',
      bestemming: json['bestemming']?.toString() ?? '',
      vertrekTyd: DateTime.parse(json['vertrek_tyd'].toString()),
      sitplekke: (json['sitplekke'] as num?)?.toInt() ?? 0,
      beskikbareSitplekke:
          (json['beskikbare_sitplekke'] as num?)?.toInt() ?? 0,
      status: json['status']?.toString() ?? '',
      isBestuurder: json['is_bestuurder'] == true,
      myStatus: json['my_status']?.toString(),
      bestuurder: SaamryUserDto.fromJson(
        Map<String, dynamic>.from(json['bestuurder'] as Map),
      ),
      lede: rawMembers
          .map((e) => SaamryGroupMemberDto.fromJson(
                Map<String, dynamic>.from(e as Map),
              ))
          .toList(),
    );
  }
}

class SaamryStatusDto {
  final List<SaamryFriendItemDto> friends;
  final List<SaamryFriendItemDto> incomingRequests;
  final List<SaamryFriendItemDto> outgoingRequests;
  final List<SaamryGroupDto> groupInvites;
  final SaamryGroupDto? myGroup;

  SaamryStatusDto({
    required this.friends,
    required this.incomingRequests,
    required this.outgoingRequests,
    required this.groupInvites,
    required this.myGroup,
  });

  factory SaamryStatusDto.fromJson(Map<String, dynamic> json) {
    List<SaamryFriendItemDto> parseFriends(dynamic raw) {
      return ((raw as List?) ?? const [])
          .map((e) => SaamryFriendItemDto.fromJson(
                Map<String, dynamic>.from(e as Map),
              ))
          .toList();
    }

    return SaamryStatusDto(
      friends: parseFriends(json['friends']),
      incomingRequests: parseFriends(json['incoming_requests']),
      outgoingRequests: parseFriends(json['outgoing_requests']),
      groupInvites: ((json['group_invites'] as List?) ?? const [])
          .map((e) => SaamryGroupDto.fromJson(
                Map<String, dynamic>.from(e as Map),
              ))
          .toList(),
      myGroup: json['my_group'] == null
          ? null
          : SaamryGroupDto.fromJson(
              Map<String, dynamic>.from(json['my_group'] as Map),
            ),
    );
  }
}


class SaamryGateMemberDto {
  final int gebruikerId;
  final String naam;
  final String van;
  final String volleNaam;
  final String nommer;
  final String rol;
  final String? fotoUrl;
  final bool isBestuurder;
  final bool opKampus;
  final String? laasteRigting;
  final DateTime? laasteTyd;
  final bool geselekteer;

  SaamryGateMemberDto({
    required this.gebruikerId,
    required this.naam,
    required this.van,
    required this.volleNaam,
    required this.nommer,
    required this.rol,
    this.fotoUrl,
    required this.isBestuurder,
    required this.opKampus,
    this.laasteRigting,
    this.laasteTyd,
    required this.geselekteer,
  });

  factory SaamryGateMemberDto.fromJson(Map<String, dynamic> json) {
    return SaamryGateMemberDto(
      gebruikerId: (json['gebruiker_id'] as num).toInt(),
      naam: json['naam']?.toString() ?? '',
      van: json['van']?.toString() ?? '',
      volleNaam: json['volle_naam']?.toString() ??
          '${json['naam'] ?? ''} ${json['van'] ?? ''}'.trim(),
      nommer: json['nommer']?.toString() ?? '',
      rol: json['rol']?.toString() ?? '',
      fotoUrl: json['foto_url']?.toString(),
      isBestuurder: json['is_bestuurder'] == true,
      opKampus: json['op_kampus'] == true,
      laasteRigting: json['laaste_rigting']?.toString(),
      laasteTyd: json['laaste_tyd'] == null
          ? null
          : DateTime.parse(json['laaste_tyd'].toString()).toLocal(),
      geselekteer: json['geselekteer'] == true,
    );
  }
}

class SaamryGatePreviewDto {
  final bool hasGroup;
  final String? rede;
  final int? groepId;
  final String? groepNaam;
  final int? bestuurderId;
  final String rigting;
  final int? kampusId;
  final List<SaamryGateMemberDto> lede;

  SaamryGatePreviewDto({
    required this.hasGroup,
    this.rede,
    this.groepId,
    this.groepNaam,
    this.bestuurderId,
    required this.rigting,
    this.kampusId,
    required this.lede,
  });

  factory SaamryGatePreviewDto.fromJson(Map<String, dynamic> json) {
    return SaamryGatePreviewDto(
      hasGroup: json['has_group'] == true,
      rede: json['rede']?.toString(),
      groepId: (json['groep_id'] as num?)?.toInt(),
      groepNaam: json['groep_naam']?.toString(),
      bestuurderId: (json['bestuurder_id'] as num?)?.toInt(),
      rigting: json['rigting']?.toString() ?? 'IN',
      kampusId: (json['kampus_id'] as num?)?.toInt(),
      lede: ((json['lede'] as List?) ?? const [])
          .map(
            (item) => SaamryGateMemberDto.fromJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList(),
    );
  }
}

class BesoekerUitnodigingDto {
  final int uitnodigingId;
  final String naam;
  final String van;
  final String selfoon;
  final String rede;
  final String otp;
  final String status;
  final DateTime geskepOp;
  final DateTime vervalOp;
  final DateTime? besluitOp;
  final int gasheerId;
  final String gasheerNaam;
  final String? gasheerSelfoon;
  final int? kampusId;
  final String? kampusNaam;

  BesoekerUitnodigingDto({
    required this.uitnodigingId,
    required this.naam,
    required this.van,
    required this.selfoon,
    required this.rede,
    required this.otp,
    required this.status,
    required this.geskepOp,
    required this.vervalOp,
    this.besluitOp,
    required this.gasheerId,
    required this.gasheerNaam,
    this.gasheerSelfoon,
    this.kampusId,
    this.kampusNaam,
  });

  factory BesoekerUitnodigingDto.fromJson(Map<String, dynamic> json) {
    final gasheerRaw = json['gasheer'];
    final gasheer = gasheerRaw is Map
        ? Map<String, dynamic>.from(gasheerRaw)
        : <String, dynamic>{};

    final kampusRaw = json['kampus'];
    final kampus = kampusRaw is Map
        ? Map<String, dynamic>.from(kampusRaw)
        : <String, dynamic>{};

    return BesoekerUitnodigingDto(
      uitnodigingId: (json['uitnodiging_id'] as num).toInt(),
      naam: json['naam']?.toString() ?? '',
      van: json['van']?.toString() ?? '',
      selfoon: json['selfoon']?.toString() ?? '',
      rede: json['rede']?.toString() ?? 'Besoek',
      otp: json['otp']?.toString() ?? '',
      status: json['status']?.toString() ?? 'HANGEND',
      geskepOp: DateTime.parse(json['geskep_op'].toString()).toLocal(),
      vervalOp: DateTime.parse(json['verval_op'].toString()).toLocal(),
      besluitOp: json['besluit_op'] == null
          ? null
          : DateTime.parse(json['besluit_op'].toString()).toLocal(),
      gasheerId: (gasheer['gebruiker_id'] as num?)?.toInt() ?? 0,
      gasheerNaam: gasheer['volle_naam']?.toString() ?? '',
      gasheerSelfoon: gasheer['selfoon']?.toString(),
      kampusId: (kampus['kampus_id'] as num?)?.toInt(),
      kampusNaam: kampus['naam']?.toString(),
    );
  }

  String get volleNaam => '$naam $van'.trim();

  bool get isHangend =>
      status == 'HANGEND' && DateTime.now().isBefore(vervalOp);

  bool get isVerstreke =>
      status == 'VERVAL' ||
      (status == 'HANGEND' && !DateTime.now().isBefore(vervalOp));
}

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
  

  static Future<Map<String, dynamic>> wagteProfileDecline({
  required int gebruikerId,
  required int kampusId,
  required String metode,
}) async {
  final response = await http.post(
    Uri.parse('$baseUrl/wagte/profile/decline'),
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (bearerToken != null && bearerToken!.trim().isNotEmpty)
        'Authorization': 'Bearer ${bearerToken!.trim()}',
    },
    body: jsonEncode({
      'gebruiker_id': gebruikerId,
      'kampus_id': kampusId,
      'metode': metode,
    }),
  );

  final decoded = jsonDecode(response.body);

  if (response.statusCode != 200 || decoded['sukses'] != true) {
    throw Exception(
      decoded['fout'] ?? decoded['detail'] ?? 'Toegang kon nie geweier word nie',
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


  /// -------------------------
  /// Saamry
  /// -------------------------

  static Map<String, String> _saamryHeaders({bool jsonBody = false}) {
    return {
      if (jsonBody) 'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (bearerToken != null && bearerToken!.trim().isNotEmpty)
        'Authorization': 'Bearer ${bearerToken!.trim()}',
    };
  }

  static dynamic _decodeSaamryResponse(http.Response response) {
    dynamic decoded;
    try {
      decoded = jsonDecode(response.body);
    } catch (_) {
      throw Exception(
        'Bedienerfout HTTP ${response.statusCode}: ${response.body}',
      );
    }

    if (response.statusCode < 200 ||
        response.statusCode >= 300 ||
        decoded is! Map ||
        decoded['sukses'] != true) {
      final message = decoded is Map
          ? (decoded['fout'] ?? decoded['detail'] ?? 'Saamry-versoek het misluk')
          : 'Saamry-versoek het misluk';
      throw Exception(message.toString());
    }

    return decoded['data'];
  }

  static Future<SaamryStatusDto> fetchSaamryStatus() async {
    final response = await http.get(
      Uri.parse('$baseUrl/saamry/status'),
      headers: _saamryHeaders(),
    );

    final data = _decodeSaamryResponse(response);
    return SaamryStatusDto.fromJson(Map<String, dynamic>.from(data as Map));
  }

  static Future<List<SaamryUserDto>> searchSaamryUsers(String query) async {
    final clean = query.trim();
    if (clean.length < 2) return [];

    final response = await http.get(
      Uri.parse(
        '$baseUrl/saamry/gebruikers/search?q=${Uri.encodeQueryComponent(clean)}',
      ),
      headers: _saamryHeaders(),
    );

    final data = _decodeSaamryResponse(response);
    return ((data as List?) ?? const [])
        .map((e) => SaamryUserDto.fromJson(
              Map<String, dynamic>.from(e as Map),
            ))
        .toList();
  }

  static Future<void> sendSaamryFriendRequest(int ontvangerId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/vriende/versoek'),
      headers: _saamryHeaders(jsonBody: true),
      body: jsonEncode({'ontvanger_id': ontvangerId}),
    );
    _decodeSaamryResponse(response);
  }

  static Future<void> acceptSaamryFriendRequest(int vriendskapId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/vriende/$vriendskapId/aanvaar'),
      headers: _saamryHeaders(),
    );
    _decodeSaamryResponse(response);
  }

  static Future<void> declineSaamryFriendRequest(int vriendskapId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/vriende/$vriendskapId/weier'),
      headers: _saamryHeaders(),
    );
    _decodeSaamryResponse(response);
  }

  static Future<void> removeSaamryFriend(int vriendId) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/saamry/vriende/$vriendId'),
      headers: _saamryHeaders(),
    );
    _decodeSaamryResponse(response);
  }

  static Future<SaamryGroupDto> createSaamryGroup({
    String? naam,
    required String vertrekpunt,
    required String bestemming,
    required DateTime vertrekTyd,
    required int sitplekke,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/groepe'),
      headers: _saamryHeaders(jsonBody: true),
      body: jsonEncode({
        'naam': naam?.trim().isEmpty == true ? null : naam?.trim(),
        'vertrekpunt': vertrekpunt.trim(),
        'bestemming': bestemming.trim(),
        'vertrek_tyd': vertrekTyd.toIso8601String(),
        'sitplekke': sitplekke,
      }),
    );

    final data = _decodeSaamryResponse(response);
    return SaamryGroupDto.fromJson(Map<String, dynamic>.from(data as Map));
  }

  static Future<void> inviteSaamryFriend({
    required int groepId,
    required int gebruikerId,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/groepe/$groepId/nooi'),
      headers: _saamryHeaders(jsonBody: true),
      body: jsonEncode({'gebruiker_id': gebruikerId}),
    );
    _decodeSaamryResponse(response);
  }

  static Future<SaamryGroupDto> acceptSaamryGroupInvite(int groepId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/groepe/$groepId/aanvaar'),
      headers: _saamryHeaders(),
    );
    final data = _decodeSaamryResponse(response);
    return SaamryGroupDto.fromJson(Map<String, dynamic>.from(data as Map));
  }

  static Future<void> declineSaamryGroupInvite(int groepId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/groepe/$groepId/weier'),
      headers: _saamryHeaders(),
    );
    _decodeSaamryResponse(response);
  }

  static Future<void> closeSaamryGroup(int groepId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/groepe/$groepId/sluit'),
      headers: _saamryHeaders(),
    );
    _decodeSaamryResponse(response);
  }

  static Future<void> leaveSaamryGroup(int groepId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/groepe/$groepId/verlaat'),
      headers: _saamryHeaders(),
    );
    _decodeSaamryResponse(response);
  }


  static Future<SaamryGatePreviewDto> wagteSaamryGatePreview({
    required int bestuurderId,
    required int kampusId,
    required String rigting,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/wagte/hek/preview'),
      headers: _saamryHeaders(jsonBody: true),
      body: jsonEncode({
        'bestuurder_id': bestuurderId,
        'kampus_id': kampusId,
        'rigting': rigting.trim().toUpperCase(),
      }),
    );

    final data = _decodeSaamryResponse(response);
    return SaamryGatePreviewDto.fromJson(
      Map<String, dynamic>.from(data as Map),
    );
  }

  static Future<Map<String, dynamic>> wagteSaamryGateConfirm({
    required int groepId,
    required int kampusId,
    required String rigting,
    required String metode,
    required List<int> gebruikerIds,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/saamry/wagte/hek/bevestig'),
      headers: _saamryHeaders(jsonBody: true),
      body: jsonEncode({
        'groep_id': groepId,
        'kampus_id': kampusId,
        'rigting': rigting.trim().toUpperCase(),
        'metode': metode.trim().toUpperCase(),
        'gebruiker_ids': gebruikerIds,
      }),
    );

    final data = _decodeSaamryResponse(response);
    return Map<String, dynamic>.from(data as Map);
  }

  /// -------------------------
  /// Besoeker OTP-uitnodigings
  /// -------------------------

  static Map<String, String> _besoekerHeaders({bool jsonBody = false}) {
    return {
      if (jsonBody) 'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (bearerToken != null && bearerToken!.trim().isNotEmpty)
        'Authorization': 'Bearer ${bearerToken!.trim()}',
    };
  }

  static dynamic _decodeBesoekerResponse(http.Response response) {
    dynamic decoded;
    try {
      decoded = jsonDecode(response.body);
    } catch (_) {
      throw Exception(
        'Bedienerfout HTTP ${response.statusCode}: ${response.body}',
      );
    }

    if (response.statusCode < 200 ||
        response.statusCode >= 300 ||
        decoded is! Map ||
        decoded['sukses'] != true) {
      final message = decoded is Map
          ? (decoded['fout'] ??
              decoded['detail'] ??
              'Besoeker-versoek het misluk')
          : 'Besoeker-versoek het misluk';
      throw Exception(message.toString());
    }

    return decoded['data'];
  }

  static Future<BesoekerUitnodigingDto> createVisitorInvite({
    required String naam,
    required String van,
    required String selfoon,
    String? rede,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/besoekers/uitnodigings'),
      headers: _besoekerHeaders(jsonBody: true),
      body: jsonEncode({
        'naam': naam.trim(),
        'van': van.trim(),
        'selfoon': selfoon.trim(),
        'rede': rede?.trim(),
      }),
    );

    final data = _decodeBesoekerResponse(response);
    return BesoekerUitnodigingDto.fromJson(
      Map<String, dynamic>.from(data as Map),
    );
  }

  static Future<List<BesoekerUitnodigingDto>> fetchMyVisitorInvites() async {
    final response = await http.get(
      Uri.parse('$baseUrl/besoekers/uitnodigings/my'),
      headers: _besoekerHeaders(),
    );

    final data = _decodeBesoekerResponse(response);
    return ((data as List?) ?? const [])
        .map(
          (e) => BesoekerUitnodigingDto.fromJson(
            Map<String, dynamic>.from(e as Map),
          ),
        )
        .toList();
  }

  static Future<BesoekerUitnodigingDto> cancelVisitorInvite(
    int uitnodigingId,
  ) async {
    final response = await http.post(
      Uri.parse(
        '$baseUrl/besoekers/uitnodigings/$uitnodigingId/kanselleer',
      ),
      headers: _besoekerHeaders(),
    );

    final data = _decodeBesoekerResponse(response);
    return BesoekerUitnodigingDto.fromJson(
      Map<String, dynamic>.from(data as Map),
    );
  }

  static Future<BesoekerUitnodigingDto> verifyVisitorOtp(String otp) async {
    final response = await http.post(
      Uri.parse('$baseUrl/besoekers/verifieer'),
      headers: _besoekerHeaders(jsonBody: true),
      body: jsonEncode({'otp': otp.trim()}),
    );

    final data = _decodeBesoekerResponse(response);
    return BesoekerUitnodigingDto.fromJson(
      Map<String, dynamic>.from(data as Map),
    );
  }

  static Future<BesoekerUitnodigingDto> allowVisitorEntry({
    required int uitnodigingId,
    required int kampusId,
  }) async {
    final response = await http.post(
      Uri.parse(
        '$baseUrl/besoekers/uitnodigings/$uitnodigingId/toelaat',
      ),
      headers: _besoekerHeaders(jsonBody: true),
      body: jsonEncode({'kampus_id': kampusId}),
    );

    final data = _decodeBesoekerResponse(response);
    return BesoekerUitnodigingDto.fromJson(
      Map<String, dynamic>.from(data as Map),
    );
  }

  static Future<BesoekerUitnodigingDto> denyVisitorEntry({
    required int uitnodigingId,
    required int kampusId,
  }) async {
    final response = await http.post(
      Uri.parse(
        '$baseUrl/besoekers/uitnodigings/$uitnodigingId/weier',
      ),
      headers: _besoekerHeaders(jsonBody: true),
      body: jsonEncode({'kampus_id': kampusId}),
    );

    final data = _decodeBesoekerResponse(response);
    return BesoekerUitnodigingDto.fromJson(
      Map<String, dynamic>.from(data as Map),
    );
  }

}



