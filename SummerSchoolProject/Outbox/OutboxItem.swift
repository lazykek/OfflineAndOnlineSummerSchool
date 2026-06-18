//
//  OutboxItem.swift
//  SummerSchoolProject
//

import Foundation

// MARK: - OutboxStatus

enum OutboxStatus: String, Codable {
    case pending
    case inFlight
    case failed
}

// MARK: - OutboxAction

enum OutboxAction: Codable, Equatable {
    case likePost(postID: Int)

    private enum CodingKeys: String, CodingKey { case type, postID }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let type = try c.decode(String.self, forKey: .type)
        switch type {
        case "likePost":
            self = .likePost(postID: try c.decode(Int.self, forKey: .postID))
        default:
            throw DecodingError.dataCorruptedError(
                forKey: .type, in: c, debugDescription: "Unknown action: \(type)")
        }
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .likePost(let id):
            try c.encode("likePost", forKey: .type)
            try c.encode(id, forKey: .postID)
        }
    }
}

// MARK: - OutboxItem

struct OutboxItem: Codable, Identifiable {
    let clientID: UUID
    var id: UUID { clientID }

    let action: OutboxAction
    let createdAt: Date
    var status: OutboxStatus
    var retryCount: Int

    init(action: OutboxAction) {
        self.clientID = UUID()
        self.action = action
        self.createdAt = Date()
        self.status = .pending
        self.retryCount = 0
    }
}
