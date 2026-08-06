import 'package:flutter/foundation.dart';
import 'domain_errors.dart';

/// Realises: [Feat-10/Result]
///
/// A generic sealed class representing either a successful outcome [Success]
/// or a domain error failure [Failure].
@immutable
sealed class Result<T> {
  /// Abstract const constructor for [Result].
  const Result();

  /// Creates a successful [Result] carrying [value].
  const factory Result.success(T value) = Success<T>;

  /// Creates a failed [Result] carrying [error].
  const factory Result.failure(DomainError error) = Failure<T>;

  /// Returns `true` if this result is a [Success].
  bool get isSuccess => this is Success<T>;

  /// Returns `true` if this result is a [Failure].
  bool get isFailure => this is Failure<T>;
}

/// Realises: [Feat-10/Result]
/// Represents a successful result carrying a payload value of type [T].
@immutable
final class Success<T> extends Result<T> {
  /// Creates a [Success] instance carrying the given [value].
  const Success(this.value);

  /// The successful payload value.
  final T value;
}

/// Realises: [Feat-10/Result]
/// Represents a failed result carrying a [DomainError].
@immutable
final class Failure<T> extends Result<T> {
  /// Creates a [Failure] instance carrying the given domain [error].
  const Failure(this.error);

  /// The domain error describing the cause of failure.
  final DomainError error;
}
