-- Fix user_notes table to work with RLS properly
-- This adds the missing unique constraint so upsert() works

-- Step 1: Add unique constraint on user_id (required for upsert with on_conflict)
ALTER TABLE user_notes
ADD CONSTRAINT user_notes_user_id_unique UNIQUE (user_id);

-- Step 2: Enable RLS
ALTER TABLE user_notes ENABLE ROW LEVEL SECURITY;

-- Step 3: Create RLS policies (with correct UUID type casting)
-- Policy 1: Users can view their own notes
CREATE POLICY "Users can view own notes"
ON user_notes
FOR SELECT
USING (auth.uid() = user_id);

-- Policy 2: Users can insert their own notes
CREATE POLICY "Users can insert own notes"
ON user_notes
FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Policy 3: Users can update their own notes
CREATE POLICY "Users can update own notes"
ON user_notes
FOR UPDATE
USING (auth.uid() = user_id);

-- Policy 4: Users can delete their own notes
CREATE POLICY "Users can delete own notes"
ON user_notes
FOR DELETE
USING (auth.uid() = user_id);

-- Step 4: Allow service role to bypass RLS (for backend operations)
CREATE POLICY "Service role has full access"
ON user_notes
FOR ALL
TO service_role
USING (true);

-- Verify the setup
SELECT
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE tablename = 'user_notes';
