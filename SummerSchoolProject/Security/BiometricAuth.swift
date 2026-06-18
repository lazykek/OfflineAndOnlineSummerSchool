//
//  BiometricAuth.swift
//  SummerSchoolProject
//

import LocalAuthentication
import Foundation

// MARK: - BiometricError

enum BiometricError: LocalizedError {
    case unavailable
    case notEnrolled
    case canceled
    case failed
    case lockout
    case other(Error)

    var errorDescription: String? {
        switch self {
        case .unavailable:  return "Биометрия недоступна на этом устройстве."
        case .notEnrolled:  return "Face ID не настроен. Перейдите в Настройки → Face ID и код-пароль."
        case .canceled:     return "Аутентификация отменена."
        case .failed:       return "Биометрия не распознана. Попробуйте ещё раз."
        case .lockout:      return "Слишком много попыток. Введите пароль устройства."
        case .other(let e): return e.localizedDescription
        }
    }
}

// MARK: - BiometryType

enum BiometryType {
    case faceID
    case touchID
    case none

    var systemImage: String {
        switch self {
        case .faceID:  return "faceid"
        case .touchID: return "touchid"
        case .none:    return "lock"
        }
    }

    var displayName: String {
        switch self {
        case .faceID:  return "Face ID"
        case .touchID: return "Touch ID"
        case .none:    return "Пароль"
        }
    }
}

// MARK: - BiometricAuth

final class BiometricAuth: Sendable {
    static let shared = BiometricAuth()
    private init() {}

    var biometryType: BiometryType {
        let ctx = LAContext()
        var error: NSError?
        guard ctx.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            return .none
        }
        switch ctx.biometryType {
        case .faceID:  return .faceID
        case .touchID: return .touchID
        default:       return .none
        }
    }

    func authenticate(
        reason: String,
        fallback: String? = nil,
        allowPasscodeFallback: Bool = false
    ) async -> Result<Void, BiometricError> {
        let ctx = LAContext()
        ctx.localizedFallbackTitle = fallback

        let policy: LAPolicy = allowPasscodeFallback
            ? .deviceOwnerAuthentication
            : .deviceOwnerAuthenticationWithBiometrics

        var policyError: NSError?
        guard ctx.canEvaluatePolicy(policy, error: &policyError) else {
            return .failure(mapLAError(policyError))
        }

        return await withCheckedContinuation { continuation in
            ctx.evaluatePolicy(
                policy,
                localizedReason: reason
            ) { success, error in
                if success {
                    continuation.resume(returning: .success(()))
                } else {
                    continuation.resume(returning: .failure(self.mapLAError(error as NSError?)))
                }
            }
        }
    }

    // MARK: - Private

    private func mapLAError(_ error: NSError?) -> BiometricError {
        guard let error else { return .failed }
        switch LAError.Code(rawValue: error.code) {
        case .biometryNotAvailable:                  return .unavailable
        case .biometryNotEnrolled:                   return .notEnrolled
        case .userCancel, .appCancel, .systemCancel: return .canceled
        case .authenticationFailed:                  return .failed
        case .biometryLockout:                       return .lockout
        default:                                     return .other(error)
        }
    }
}
