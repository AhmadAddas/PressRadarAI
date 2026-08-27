"use client";

import {
  ChangeEvent,
  ClipboardEvent,
  KeyboardEvent,
  useRef,
  useState,
} from "react";

type OTPInputProps = {
  label: string;
  name: string;
  autoFocus?: boolean;
};

const CODE_LENGTH = 6;

export function OTPInput({ label, name, autoFocus = false }: OTPInputProps) {
  const [digits, setDigits] = useState(() =>
    Array<string>(CODE_LENGTH).fill(""),
  );
  const inputs = useRef<Array<HTMLInputElement | null>>([]);

  function fillFrom(index: number, value: string) {
    const incoming = value.replace(/\D/g, "").slice(0, CODE_LENGTH - index);
    if (!incoming) return;
    setDigits((current) => {
      const next = [...current];
      [...incoming].forEach((digit, offset) => {
        next[index + offset] = digit;
      });
      return next;
    });
    inputs.current[Math.min(index + incoming.length, CODE_LENGTH - 1)]?.focus();
  }

  function change(index: number, event: ChangeEvent<HTMLInputElement>) {
    const incoming = event.currentTarget.value.replace(/\D/g, "");
    if (incoming.length > 1) {
      fillFrom(index, incoming);
      return;
    }
    setDigits((current) => {
      const next = [...current];
      next[index] = incoming;
      return next;
    });
    if (incoming && index < CODE_LENGTH - 1) inputs.current[index + 1]?.focus();
  }

  function keyDown(index: number, event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowLeft" && index > 0)
      inputs.current[index - 1]?.focus();
    if (event.key === "ArrowRight" && index < CODE_LENGTH - 1) {
      inputs.current[index + 1]?.focus();
    }
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      setDigits((current) => {
        const next = [...current];
        next[index - 1] = "";
        return next;
      });
      inputs.current[index - 1]?.focus();
    }
  }

  function paste(index: number, event: ClipboardEvent<HTMLInputElement>) {
    event.preventDefault();
    fillFrom(index, event.clipboardData.getData("text"));
  }

  return (
    <fieldset className="otp-fieldset">
      <legend>{label}</legend>
      <div className="otp-inputs">
        {digits.map((digit, index) => (
          <input
            // Positions are stable and the digits themselves may be duplicated.
            key={index}
            ref={(element) => {
              inputs.current[index] = element;
            }}
            type="text"
            inputMode="numeric"
            autoComplete={index === 0 ? "one-time-code" : "off"}
            pattern="[0-9]*"
            maxLength={1}
            required
            value={digit}
            aria-label={`${label}, digit ${index + 1}`}
            autoFocus={autoFocus && index === 0}
            onChange={(event) => change(index, event)}
            onKeyDown={(event) => keyDown(index, event)}
            onPaste={(event) => paste(index, event)}
          />
        ))}
      </div>
      <input type="hidden" name={name} value={digits.join("")} />
    </fieldset>
  );
}
