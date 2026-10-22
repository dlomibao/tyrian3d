// C integer semantics for the OpenTyrian port. Tyrian's logic leans on fixed-width types
// (JE_byte = u8, JE_shortint = s8, JE_integer = s16, JE_word = u16, JE_longint = s32) and their
// wrap-around; apply these on assignment wherever a value can leave its type's range.

export const u8 = (v: number): number => v & 0xff;
export const s8 = (v: number): number => (v << 24) >> 24;
export const u16 = (v: number): number => v & 0xffff;
export const s16 = (v: number): number => (v << 16) >> 16;
export const u32 = (v: number): number => v >>> 0;
export const s32 = (v: number): number => v | 0;

/** C integer division (truncates toward zero). */
export const idiv = (a: number, b: number): number => Math.trunc(a / b);
